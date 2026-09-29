from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .usb_device_profiles import AIC_33C3_0E02

SYS_USB_DEVICES = Path("/sys/bus/usb/devices")


@dataclass(frozen=True, slots=True)
class UsbEndpointInventory:
    address: str | None
    attributes: str | None
    max_packet_size: str | None
    direction: str | None = None
    transfer_type: str | None = None


@dataclass(frozen=True, slots=True)
class UsbInterfaceInventory:
    name: str
    number: str | None
    alternate_setting: str | None
    class_code: str | None
    subclass_code: str | None
    protocol_code: str | None
    driver: str | None
    endpoints: tuple[UsbEndpointInventory, ...]


@dataclass(frozen=True, slots=True)
class ArtInChipUsbInventory:
    status: str
    sysfs_name: str | None = None
    busnum: int | None = None
    devnum: int | None = None
    device_node: str | None = None
    device_class: str | None = None
    interfaces: tuple[UsbInterfaceInventory, ...] = ()
    profile_key: str | None = None
    profile_name: str | None = None
    vid_pid: str | None = None
    match_count: int = 0
    ambiguous: bool = False


def _read_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return None
    return value or None


def _read_int(path: Path) -> int | None:
    value = _read_text(path)
    if value is None:
        return None
    try:
        return int(value, 10)
    except ValueError:
        return None


def _hex_byte(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        decoded = int(value, 16)
    except ValueError:
        return None
    if not 0 <= decoded <= 0xFF:
        return None
    return decoded


def _endpoint_direction(address: str | None) -> str | None:
    decoded = _hex_byte(address)
    if decoded is None:
        return None
    return "IN" if decoded & 0x80 else "OUT"


def _endpoint_transfer_type(attributes: str | None) -> str | None:
    decoded = _hex_byte(attributes)
    if decoded is None:
        return None
    return {
        0: "Control",
        1: "Isochronous",
        2: "Bulk",
        3: "Interrupt",
    }[decoded & 0x03]


def _driver_name(interface: Path) -> str | None:
    driver = interface / "driver"
    try:
        if not driver.exists():
            return None
        return driver.resolve(strict=True).name
    except OSError:
        return None


def _endpoint_inventory(interface: Path) -> tuple[UsbEndpointInventory, ...]:
    try:
        children = sorted(interface.iterdir(), key=lambda path: path.name)
    except OSError:
        return ()

    endpoints: list[UsbEndpointInventory] = []
    for child in children:
        if not child.name.startswith("ep_"):
            continue
        address = _read_text(child / "bEndpointAddress")
        attributes = _read_text(child / "bmAttributes")
        endpoints.append(
            UsbEndpointInventory(
                address=address,
                attributes=attributes,
                max_packet_size=_read_text(child / "wMaxPacketSize"),
                direction=_endpoint_direction(address),
                transfer_type=_endpoint_transfer_type(attributes),
            )
        )
    return tuple(endpoints)


def _interface_inventory(root: Any, device_name: str) -> tuple[UsbInterfaceInventory, ...]:
    try:
        entries = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError:
        return ()

    interfaces: list[UsbInterfaceInventory] = []
    prefix = f"{device_name}:"
    for entry in entries:
        if not entry.name.startswith(prefix):
            continue
        interfaces.append(
            UsbInterfaceInventory(
                name=entry.name,
                number=_read_text(entry / "bInterfaceNumber"),
                alternate_setting=_read_text(entry / "bAlternateSetting"),
                class_code=_read_text(entry / "bInterfaceClass"),
                subclass_code=_read_text(entry / "bInterfaceSubClass"),
                protocol_code=_read_text(entry / "bInterfaceProtocol"),
                driver=_driver_name(entry),
                endpoints=_endpoint_inventory(entry),
            )
        )
    return tuple(interfaces)


def _base_inventory(status: str) -> ArtInChipUsbInventory:
    profile = AIC_33C3_0E02
    return ArtInChipUsbInventory(
        status=status,
        profile_key=profile.key,
        profile_name=profile.name,
        vid_pid=profile.vid_pid,
    )


def probe_artinchip_usb_inventory(sys_usb: Any = SYS_USB_DEVICES) -> ArtInChipUsbInventory:
    """Inspect the verified ArtInChip profile through sysfs only.

    This probe deliberately does not import PyUSB, open the USB device, claim an
    interface, authenticate, send control transfers, or write endpoint data. It
    reports ambiguity explicitly when multiple exact verified matches are present.
    """
    profile = AIC_33C3_0E02
    try:
        if not sys_usb.is_dir():
            return _base_inventory("absent")
        entries = sorted(sys_usb.iterdir(), key=lambda path: path.name)
    except OSError:
        return _base_inventory("unknown")

    matches = []
    for device in entries:
        if ":" in device.name:
            continue
        vendor = _read_text(device / "idVendor")
        product = _read_text(device / "idProduct")
        if vendor == profile.sysfs_vendor_id and product == profile.sysfs_product_id:
            matches.append(device)

    if not matches:
        return _base_inventory("absent")

    device = matches[0]
    busnum = _read_int(device / "busnum")
    devnum = _read_int(device / "devnum")
    device_node = None
    if busnum is not None and devnum is not None:
        device_node = f"/dev/bus/usb/{busnum:03d}/{devnum:03d}"

    return ArtInChipUsbInventory(
        status="present",
        sysfs_name=device.name,
        busnum=busnum,
        devnum=devnum,
        device_node=device_node,
        device_class=_read_text(device / "bDeviceClass"),
        interfaces=_interface_inventory(sys_usb, device.name),
        profile_key=profile.key,
        profile_name=profile.name,
        vid_pid=profile.vid_pid,
        match_count=len(matches),
        ambiguous=len(matches) > 1,
    )
