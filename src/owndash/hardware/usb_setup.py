from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from owndash.core.subprocess_env import system_subprocess_env
from owndash.hardware.usb_device_profiles import AIC_33C3_0E02


# Compatibility aliases for existing setup/tests; the verified profile is the
# authoritative source of the actual USB identity.
USB_VENDOR_ID = AIC_33C3_0E02.sysfs_vendor_id
USB_PRODUCT_ID = AIC_33C3_0E02.sysfs_product_id
SYS_USB_DEVICES = Path("/sys/bus/usb/devices")
RULE_NAME = "70-owndash-usb.rules"
LEGACY_RULE_NAME = "99-owndash-usb.rules"
UDEV_RULE_DIR = Path("/etc/udev/rules.d")


@dataclass(frozen=True, slots=True)
class UsbAccessStatus:
    connected: bool
    accessible: bool
    device_node: str | None = None
    match_count: int = 0
    ambiguous: bool = False


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def legacy_udev_rule_installed() -> bool:
    """Return whether the obsolete late 99-* uaccess rule is still installed."""
    return (UDEV_RULE_DIR / LEGACY_RULE_NAME).is_file()


def probe_owndash_udev_state() -> str:
    """Return OwnDash's udev-rule state without mutating or opening hardware."""
    try:
        if not hasattr(UDEV_RULE_DIR, "iterdir"):
            return "unknown"
        entries = {entry.name for entry in UDEV_RULE_DIR.iterdir()}
    except OSError:
        return "unknown"

    if LEGACY_RULE_NAME in entries:
        return "legacy"
    if RULE_NAME in entries:
        return "ok"
    return "missing"


def probe_artinchip_usb(sys_usb: Path = SYS_USB_DEVICES) -> UsbAccessStatus:
    """Detect exact verified ArtInChip matches without requiring PyUSB access.

    A legacy 99-* OwnDash uaccess rule is treated as not ready even when the
    current device node happens to be accessible. Multiple exact compatible
    devices are reported explicitly instead of being silently collapsed into a
    single unambiguous result.
    """
    profile = AIC_33C3_0E02
    try:
        if not sys_usb.is_dir():
            return UsbAccessStatus(False, False, None)
        entries = sorted(sys_usb.iterdir(), key=lambda path: path.name)
    except OSError:
        return UsbAccessStatus(False, False, None)

    matches: list[Path] = []
    for device in entries:
        if ":" in device.name:
            continue
        vendor = _read(device / "idVendor").lower()
        product = _read(device / "idProduct").lower()
        if vendor == profile.sysfs_vendor_id and product == profile.sysfs_product_id:
            matches.append(device)

    if not matches:
        return UsbAccessStatus(False, False, None)

    device = matches[0]
    count = len(matches)
    try:
        bus = int(_read(device / "busnum"))
        dev = int(_read(device / "devnum"))
    except ValueError:
        return UsbAccessStatus(True, False, None, match_count=count, ambiguous=count > 1)

    node = Path(f"/dev/bus/usb/{bus:03d}/{dev:03d}")
    accessible = (
        node.exists()
        and os.access(node, os.R_OK | os.W_OK)
        and not legacy_udev_rule_installed()
    )
    return UsbAccessStatus(
        True,
        accessible,
        str(node),
        match_count=count,
        ambiguous=count > 1,
    )


def can_offer_graphical_setup() -> bool:
    return shutil.which("pkexec") is not None and shutil.which("install") is not None


def install_udev_rule() -> tuple[bool, str]:
    """Install OwnDash's udev rule after an explicit user action.

    A single pkexec invocation performs all privileged setup steps so the user
    only has to authenticate once. No privileged command is run automatically
    at application startup.

    The uaccess tag intentionally lives in a 70-* rule. systemd-logind applies
    seat ACLs later in the udev rule chain, so a legacy 99-* rule can appear to
    work initially but lose access when the USB display re-enumerates after
    suspend. Re-running setup migrates that old rule in the same authentication.
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

        destination = str(UDEV_RULE_DIR / RULE_NAME)
        legacy_destination = str(UDEV_RULE_DIR / LEGACY_RULE_NAME)

        commands = [
            f'install -m 0644 "{temp_path}" "{destination}"',
            f'rm -f "{legacy_destination}"',
        ]
        if udevadm:
            commands.extend(
                [
                    "udevadm control --reload-rules",
                    (
                        "udevadm trigger --subsystem-match=usb "
                        f"--attr-match=idVendor={AIC_33C3_0E02.sysfs_vendor_id} "
                        f"--attr-match=idProduct={AIC_33C3_0E02.sysfs_product_id}"
                    ),
                ]
            )

        command = " && ".join(commands)
        result = subprocess.run(
            [pkexec, "/bin/sh", "-c", command],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=system_subprocess_env(),
        )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if result.returncode in {126, 127}:
                return False, "Die Administratorfreigabe wurde abgebrochen."
            return False, detail or "Die USB-Regel konnte nicht installiert werden."

        # udev/logind may need a moment to install the seat ACL on the existing
        # device node after the rule reload and targeted re-trigger.
        for _ in range(15):
            if probe_artinchip_usb().accessible:
                return True, "USB-Zugriff wurde erfolgreich eingerichtet."
            time.sleep(0.2)

        status = probe_artinchip_usb()
        if status.connected:
            return False, (
                "Die USB-Regel wurde installiert, aber der Zugriff ist noch nicht aktiv. "
                "Bitte trenne das Display kurz und verbinde es erneut."
            )

        return False, (
            "Die USB-Regel wurde installiert, aber das Display wurde anschließend nicht mehr erkannt. "
            "Bitte verbinde das Display erneut."
        )

    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"USB-Einrichtung fehlgeschlagen: {exc}"
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
