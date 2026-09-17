from __future__ import annotations

import pytest

from owndash.core.display import DisplayProtocolError
from owndash.hardware.aic_usb import AicUsbDisplayBackend


def test_supported_device_controls_remain_disabled_until_transport_is_hardware_verified():
    backend = AicUsbDisplayBackend()
    caps = backend.get_capabilities()

    assert caps.hardware_brightness is False
    assert caps.device_version is False
    assert caps.panel_info is False
    assert caps.expansion_mode is False
    assert caps.startup_image is False
    assert caps.startup_video is False
    assert caps.hardware_screen_off is False
    assert caps.firmware_upgrade is False


def test_unverified_hardware_controls_do_not_send_usb_packets():
    backend = AicUsbDisplayBackend()

    assert backend.get_device_version() is None
    assert backend.get_expansion_mode() is None

    with pytest.raises(DisplayProtocolError):
        backend.set_brightness(50)

    with pytest.raises(DisplayProtocolError):
        backend.set_expansion_mode(True)
