from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


USB_VENDOR_ID = "33c3"
USB_PRODUCT_ID = "0e02"
RULE_NAME = "99-owndash-usb.rules"


@dataclass(frozen=True, slots=True)
class UsbAccessStatus:
    connected: bool
    accessible: bool
    device_node: str | None = None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def probe_artinchip_usb() -> UsbAccessStatus:
    """Detect the supported USB controller without requiring PyUSB access."""
    sys_usb = Path("/sys/bus/usb/devices")
    if not sys_usb.is_dir():
        return UsbAccessStatus(False, False, None)

    for device in sys_usb.iterdir():
        vendor = _read(device / "idVendor").lower()
        product = _read(device / "idProduct").lower()
        if vendor != USB_VENDOR_ID or product != USB_PRODUCT_ID:
            continue

        try:
            bus = int(_read(device / "busnum"))
            dev = int(_read(device / "devnum"))
        except ValueError:
            return UsbAccessStatus(True, False, None)

        node = Path(f"/dev/bus/usb/{bus:03d}/{dev:03d}")
        accessible = node.exists() and os.access(node, os.R_OK | os.W_OK)
        return UsbAccessStatus(True, accessible, str(node))

    return UsbAccessStatus(False, False, None)


def can_offer_graphical_setup() -> bool:
    return shutil.which("pkexec") is not None and shutil.which("install") is not None


def install_udev_rule() -> tuple[bool, str]:
    """Install OwnDash's udev rule after an explicit user action.

    pkexec provides the normal desktop administrator-authentication dialog.
    No privileged command is run automatically at application startup.
    """
    pkexec = shutil.which("pkexec")
    install = shutil.which("install")
    udevadm = shutil.which("udevadm")
    if not pkexec or not install:
        return False, "Die grafische Administratorfreigabe (pkexec) ist auf diesem System nicht verfügbar."

    try:
        packaged = resources.files("owndash").joinpath("resources", RULE_NAME)
        rule_text = packaged.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return False, "Die OwnDash-USB-Regel konnte im Programmpaket nicht gefunden werden."

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="owndash-", suffix=".rules", delete=False
        ) as handle:
            handle.write(rule_text)
            temp_path = Path(handle.name)

        destination = f"/etc/udev/rules.d/{RULE_NAME}"
        result = subprocess.run(
            [pkexec, install, "-m", "0644", str(temp_path), destination],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if result.returncode in {126, 127}:
                return False, "Die Administratorfreigabe wurde abgebrochen."
            return False, detail or "Die USB-Regel konnte nicht installiert werden."

        if udevadm:
            subprocess.run(
                [pkexec, udevadm, "control", "--reload-rules"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            subprocess.run(
                [
                    pkexec, udevadm, "trigger",
                    "--subsystem-match=usb",
                    f"--attr-match=idVendor={USB_VENDOR_ID}",
                    f"--attr-match=idProduct={USB_PRODUCT_ID}",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        return True, "USB-Zugriff wurde eingerichtet. Falls das Display noch nicht erkannt wird, trenne es kurz und verbinde es erneut."
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"USB-Einrichtung fehlgeschlagen: {exc}"
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
