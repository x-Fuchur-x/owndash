from owndash.hardware.usb_device_profiles import (
    AIC_33C3_0E02,
    SUPPORTED_USB_DEVICE_PROFILES,
    find_usb_device_profile,
)


def test_verified_artinchip_profile_has_stable_identity_and_formats():
    profile = AIC_33C3_0E02

    assert profile.key == "artinchip-33c3-0e02"
    assert profile.name == "ArtInChip / VSDISPLAY 33C3:0E02"
    assert profile.vendor_id == 0x33C3
    assert profile.product_id == 0x0E02
    assert profile.sysfs_vendor_id == "33c3"
    assert profile.sysfs_product_id == "0e02"
    assert profile.vid_pid == "33C3:0E02"


def test_supported_registry_contains_only_verified_profiles():
    assert SUPPORTED_USB_DEVICE_PROFILES == (AIC_33C3_0E02,)


def test_profile_lookup_is_exact_and_does_not_wildcard_artinchip_family():
    assert find_usb_device_profile(0x33C3, 0x0E02) is AIC_33C3_0E02
    assert find_usb_device_profile("33c3", "0e02") is AIC_33C3_0E02
    assert find_usb_device_profile("33C3", "0E02") is AIC_33C3_0E02

    assert find_usb_device_profile(0x33C3, 0x0E01) is None
    assert find_usb_device_profile("33c3", "ffff") is None
    assert find_usb_device_profile("zzzz", "0e02") is None
