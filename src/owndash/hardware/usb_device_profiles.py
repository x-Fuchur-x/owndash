from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UsbDeviceProfile:
    """Verified direct-USB device identity used across detection and transport."""

    key: str
    name: str
    vendor_id: int
    product_id: int

    @property
    def sysfs_vendor_id(self) -> str:
        return f"{self.vendor_id:04x}"

    @property
    def sysfs_product_id(self) -> str:
        return f"{self.product_id:04x}"

    @property
    def vid_pid(self) -> str:
        return f"{self.vendor_id:04X}:{self.product_id:04X}"


AIC_33C3_0E02 = UsbDeviceProfile(
    key="artinchip-33c3-0e02",
    name="ArtInChip / VSDISPLAY 33C3:0E02",
    vendor_id=0x33C3,
    product_id=0x0E02,
)

SUPPORTED_USB_DEVICE_PROFILES = (AIC_33C3_0E02,)


def _normalize_usb_id(value: int | str) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 0xFFFF else None
    try:
        text = str(value).strip()
        if not text:
            return None
        decoded = int(text, 16)
    except (TypeError, ValueError):
        return None
    return decoded if 0 <= decoded <= 0xFFFF else None


def find_usb_device_profile(
    vendor_id: int | str,
    product_id: int | str,
) -> UsbDeviceProfile | None:
    """Return an exact verified profile; never infer support from vendor family."""

    vendor = _normalize_usb_id(vendor_id)
    product = _normalize_usb_id(product_id)
    if vendor is None or product is None:
        return None
    for profile in SUPPORTED_USB_DEVICE_PROFILES:
        if profile.vendor_id == vendor and profile.product_id == product:
            return profile
    return None
