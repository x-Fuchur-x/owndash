from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

USB_VENDOR_ID = "33c3"
USB_PRODUCT_ID = "0e02"
SYS_USB_DEVICES = Path("/sys/bus/usb/devices")


@dataclass(frozen=True, slots=True)
class UsbEndpointInventory:
    address: str | None
    attributes: str | None
    max_packet_size: str | None


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
        endpoints.append(
            UsbEndpointInventory(
                address=_read_text(child / "bEndpointAddress"),
                attributes=_read_text(child / "bmAttributes"),
                max_packet_size=_read_text(child / "wMaxPacketSize"),
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


def probe_artinchip_usb_inventory(sys_usb: Any = SYS_USB_DEVICES) -> ArtInChipUsbInventory:
    """Inspect the supported ArtInChip device through sysfs only.

    This probe deliberately does not import PyUSB, open the USB device, claim an
    interface, authenticate, send control transfers, or write endpoint data. It
    is intended to gather hardware evidence before optional device controls are
    ever enabled.
    """
    try:
        if not sys_usb.is_dir():
            return ArtInChipUsbInventory(status="absent")
        entries = sorted(sys_usb.iterdir(), key=lambda path: path.name)
    except OSError:
        return ArtInChipUsbInventory(status="unknown")

    for device in entries:
        if ":" in device.name:
            continue
        vendor = _read_text(device / "idVendor")
        product = _read_text(device / "idProduct")
        if vendor != USB_VENDOR_ID or product != USB_PRODUCT_ID:
            continue

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
        )

    return ArtInChipUsbInventory(status="absent")
