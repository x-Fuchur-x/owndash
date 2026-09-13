from __future__ import annotations

import io
import os
import secrets
import subprocess
from dataclasses import dataclass
from typing import Any

from PIL import Image
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

from owndash.core.display import DisplayBackend, DisplayBusyError, DisplayInfo, DisplayNotFoundError, DisplayProtocolError

from .aic_protocol import AUTH_DEVICE_MAGIC, AUTH_HOST_MAGIC, FRAME_START_MAGIC, make_command_header, parse_display_parameters

# USB identity used by the currently supported 8.8-inch bar-display controller.
USB_VENDOR_ID = 0x33C3
USB_PRODUCT_ID = 0x0E02
EP_OUT = 0x01
EP_IN = 0x81
MAX_TRANSFER = 256 * 1024

# Public authentication key required by the compatible display firmware.  It is
# protocol data, not application branding or executable third-party source code.
_RSA_PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAybdtvB1uNA4XICh+xJi1
KJWO0GYal4lNiW69zSMIJFGzb2wkiFBX2txFaH5ZYh0TYdwmjzBqinzTsWhIasW3
rl9QN5cv73zFalO3J4hADXz1g7hlHVB0BKDD280NUKUGAbwDv+KMHTprs+B/T4QU
a0s4RBNnN4fMPk2H0UAWU1jKAvMYjh/YR+MLYbl04ZCLlOfX9zQjRBVan7aLARQg
v5QRahAlAoBsYK864VrBKq91lRCXt4XP5d/sDtZM7kGcpLi2i4xHtRct37M+bkZv
Lf/3aVpAVsqZy5P2NXEe6HMv4Q+YP6QKz2wuk3xWYHWFn+88ydjv394tN28rjl56
hwIDAQAB
-----END PUBLIC KEY-----"""


@dataclass(slots=True)
class UsbBackendSettings:
    rotation: int = 270
    jpeg_quality: int = 84
    block_size: int = MAX_TRANSFER
    check_conflicting_service: bool = True


class AicUsbDisplayBackend(DisplayBackend):
    """Direct userspace USB transport for the currently supported bar display.

    The implementation is intentionally isolated behind ``DisplayBackend`` so
    additional display families can be added without changing the editor.
    """

    def __init__(self, settings: UsbBackendSettings | None = None):
        self.settings = settings or UsbBackendSettings()
        self._usb_core: Any = None
        self._usb_util: Any = None
        self._dev: Any = None
        self._format = 0
        self._frame_id = 0
        self._info: DisplayInfo | None = None

    @staticmethod
    def _legacy_service_active() -> bool:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", "tinyscreen.service"],
                check=False,
                timeout=1.5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    @staticmethod
    def _load_usb() -> tuple[Any, Any]:
        try:
            import usb.core  # type: ignore[import-not-found]
            import usb.util  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DisplayProtocolError("PyUSB ist nicht installiert.") from exc
        return usb.core, usb.util

    def connect(self) -> DisplayInfo:
        if self.settings.check_conflicting_service and self._legacy_service_active():
            raise DisplayBusyError(
                "Ein anderer Display-Dienst verwendet das USB-Display. "
                "Beende ihn zuerst, bevor OwnDash die direkte Ausgabe übernimmt."
            )

        usb_core, usb_util = self._load_usb()
        self._usb_core, self._usb_util = usb_core, usb_util
        dev = usb_core.find(idVendor=USB_VENDOR_ID, idProduct=USB_PRODUCT_ID)
        if dev is None:
            raise DisplayNotFoundError("Kein kompatibles USB-Display gefunden.")

        try:
            try:
                if dev.is_kernel_driver_active(0):
                    dev.detach_kernel_driver(0)
            except (NotImplementedError, usb_core.USBError):
                pass
            usb_util.claim_interface(dev, 0)
            params = dev.ctrl_transfer(
                usb_util.CTRL_IN | usb_util.CTRL_TYPE_VENDOR | usb_util.CTRL_RECIPIENT_DEVICE,
                0,
                0,
                0,
                256,
                timeout=5000,
            )
            width, height, media_format, fps = parse_display_parameters(bytes(params))
            self._authenticate(dev)
        except usb_core.USBError as exc:
            self._dev = None
            try:
                usb_util.release_interface(dev, 0)
            except Exception:
                pass
            if getattr(exc, "errno", None) in {13, -3}:
                raise DisplayProtocolError(
                    "Keine Zugriffsrechte auf das USB-Display. Die OwnDash-udev-Regel ist noch nicht installiert."
                ) from exc
            if getattr(exc, "errno", None) in {16, -6}:
                raise DisplayBusyError("Das USB-Display wird bereits von einem anderen Prozess verwendet.") from exc
            raise DisplayProtocolError(f"USB-Verbindung fehlgeschlagen: {exc}") from exc
        except Exception:
            self._dev = None
            try:
                usb_util.release_interface(dev, 0)
            except Exception:
                pass
            raise

        self._dev = dev
        self._format = media_format
        self._frame_id = 0
        self._info = DisplayInfo("USB Bar Display", width, height, fps or None)
        return self._info

    def _bulk_out(self, payload: bytes, timeout: int = 5000) -> None:
        if self._dev is None:
            raise DisplayProtocolError("Display ist nicht verbunden.")
        self._dev.write(EP_OUT, payload, timeout=timeout)

    def _bulk_in(self, size: int, timeout: int = 5000) -> bytes:
        if self._dev is None:
            raise DisplayProtocolError("Display ist nicht verbunden.")
        return bytes(self._dev.read(EP_IN, size, timeout=timeout))

    @staticmethod
    def _rsa_recover(public_key: Any, ciphertext: bytes) -> bytes:
        numbers = public_key.public_numbers()
        value = pow(int.from_bytes(ciphertext, "big"), numbers.e, numbers.n)
        decoded = value.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
        if len(decoded) < 3 or decoded[:2] != b"\x00\x01":
            raise DisplayProtocolError("Ungültige Authentifizierungsantwort.")
        separator = decoded.find(b"\x00", 2)
        if separator < 10 or any(byte != 0xFF for byte in decoded[2:separator]):
            raise DisplayProtocolError("Ungültige Authentifizierungspolsterung.")
        return decoded[separator + 1 :]

    def _authenticate(self, dev: Any) -> None:
        # Assign before the handshake so the bulk helpers can use the device.
        self._dev = dev
        key = serialization.load_pem_public_key(_RSA_PUBLIC_KEY)
        challenge = os.urandom(secrets.randbelow(244) + 1)
        encrypted = key.encrypt(challenge, asym_padding.PKCS1v15())

        self._bulk_out(make_command_header(AUTH_DEVICE_MAGIC, 0x100))
        self._bulk_out(encrypted)
        response = self._bulk_in(256, timeout=3000)
        if response[: len(challenge)] != challenge:
            self._dev = None
            raise DisplayProtocolError("Display-Authentifizierung fehlgeschlagen.")

        self._bulk_out(make_command_header(AUTH_HOST_MAGIC, 0x100))
        signed = self._bulk_in(256, timeout=3000)
        plaintext = self._rsa_recover(key, signed)
        self._bulk_out(plaintext)

    def _prepare_jpeg(self, payload: bytes) -> bytes:
        rotation = self.settings.rotation % 360
        if rotation == 0:
            return payload
        if rotation not in {90, 180, 270}:
            raise DisplayProtocolError("Rotation muss 0, 90, 180 oder 270 Grad sein.")
        try:
            with Image.open(io.BytesIO(payload)) as source:
                image = source.convert("RGB").rotate(-rotation, expand=True)
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=max(50, min(95, self.settings.jpeg_quality)))
                return output.getvalue()
        except OSError as exc:
            raise DisplayProtocolError("Ungültiger JPEG-Frame.") from exc

    def send_jpeg(self, payload: bytes) -> None:
        if self._dev is None:
            raise DisplayProtocolError("Display ist nicht verbunden.")
        frame = self._prepare_jpeg(payload)
        header = make_command_header(FRAME_START_MAGIC, len(frame), self._frame_id, self._format)
        try:
            self._bulk_out(header)
            block_size = max(4096, min(1024 * 1024, self.settings.block_size))
            for offset in range(0, len(frame), block_size):
                self._bulk_out(frame[offset : offset + block_size], timeout=10000)
        except Exception as exc:
            # One clear-halt retry handles transient USB endpoint stalls while
            # still surfacing persistent failures to the stream controller.
            try:
                if self._usb_util is not None:
                    self._dev.clear_halt(EP_OUT)
                self._bulk_out(header)
                for offset in range(0, len(frame), block_size):
                    self._bulk_out(frame[offset : offset + block_size], timeout=10000)
            except Exception as retry_exc:
                raise DisplayProtocolError(f"USB-Übertragung fehlgeschlagen: {retry_exc}") from exc
        self._frame_id = (self._frame_id + 1) & 0xFFFF

    def close(self) -> None:
        dev, util = self._dev, self._usb_util
        self._dev = None
        self._info = None
        if dev is not None and util is not None:
            try:
                util.release_interface(dev, 0)
            except Exception:
                pass
            try:
                util.dispose_resources(dev)
            except Exception:
                pass
