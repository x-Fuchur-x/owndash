from __future__ import annotations

import fcntl
import os
from pathlib import Path
import select
import termios
import time

from owndash.core.display import DisplayProtocolError


USB_VENDOR_ID = "33c3"
USB_PRODUCT_ID = "0e02"
CONTROL_BAUD = 1_000_000


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return ""


def _belongs_to_supported_usb_device(device_path: Path) -> bool:
    current = device_path.resolve()
    for parent in (current, *current.parents):
        if _read_text(parent / "idVendor") == USB_VENDOR_ID and _read_text(parent / "idProduct") == USB_PRODUCT_ID:
            return True
    return False


def find_control_tty(sys_class_tty: Path = Path("/sys/class/tty"), dev_root: Path = Path("/dev")) -> Path | None:
    """Return the tty node belonging to the supported ArtInChip USB device."""
    if not sys_class_tty.is_dir():
        return None
    for tty in sorted(sys_class_tty.iterdir()):
        device_link = tty / "device"
        if not device_link.exists() or not _belongs_to_supported_usb_device(device_link):
            continue
        node = dev_root / tty.name
        if node.exists():
            return node
    return None


class AicCdcControlTransport:
    """Linux CDC/serial control channel used by compatible ArtInChip displays."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self._fd: int | None = None

    @property
    def is_open(self) -> bool:
        return self._fd is not None

    def open(self) -> None:
        if self._fd is not None:
            return
        path = self.path or find_control_tty()
        if path is None:
            raise DisplayProtocolError("Kein ArtInChip-Steuerkanal gefunden.")
        try:
            fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            attrs = termios.tcgetattr(fd)
            attrs[0] = 0
            attrs[1] = 0
            attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
            if hasattr(termios, "CRTSCTS"):
                attrs[2] &= ~termios.CRTSCTS
            attrs[3] = 0
            attrs[4] = termios.B1000000
            attrs[5] = termios.B1000000
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 1
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
            termios.tcflush(fd, termios.TCIOFLUSH)
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
        except (OSError, termios.error) as exc:
            try:
                os.close(fd)
            except (OSError, UnboundLocalError):
                pass
            raise DisplayProtocolError(f"ArtInChip-Steuerkanal konnte nicht geöffnet werden: {exc}") from exc
        self.path = path
        self._fd = fd

    def close(self) -> None:
        fd = self._fd
        self._fd = None
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    def write(self, payload: bytes) -> None:
        if self._fd is None:
            raise DisplayProtocolError("ArtInChip-Steuerkanal ist nicht geöffnet.")
        view = memoryview(payload)
        try:
            while view:
                written = os.write(self._fd, view)
                if written <= 0:
                    raise OSError("short write")
                view = view[written:]
        except OSError as exc:
            raise DisplayProtocolError(f"Steuerbefehl konnte nicht gesendet werden: {exc}") from exc

    def read_response(self, expected_command: int, minimum_length: int, timeout: float = 1.0) -> bytes:
        """Read one 5A A5 response, waiting for a short quiet gap after data arrives."""
        if self._fd is None:
            raise DisplayProtocolError("ArtInChip-Steuerkanal ist nicht geöffnet.")
        deadline = time.monotonic() + timeout
        quiet_deadline: float | None = None
        buffer = bytearray()
        while time.monotonic() < deadline:
            now = time.monotonic()
            wait_until = min(deadline, quiet_deadline) if quiet_deadline is not None else deadline
            readable, _, _ = select.select([self._fd], [], [], max(0.0, wait_until - now))
            if readable:
                try:
                    chunk = os.read(self._fd, 4096)
                except OSError as exc:
                    raise DisplayProtocolError(f"Steuerantwort konnte nicht gelesen werden: {exc}") from exc
                if chunk:
                    buffer.extend(chunk)
                    quiet_deadline = time.monotonic() + 0.03
                    continue
            if quiet_deadline is not None and time.monotonic() >= quiet_deadline:
                break

        start = bytes(buffer).find(b"\x5a\xa5")
        if start < 0:
            raise DisplayProtocolError("Keine gültige ArtInChip-Steuerantwort empfangen.")
        packet = bytes(buffer[start:])
        if len(packet) < minimum_length or len(packet) < 4 or packet[3] != expected_command:
            raise DisplayProtocolError("Unerwartete oder unvollständige ArtInChip-Steuerantwort.")
        return packet
