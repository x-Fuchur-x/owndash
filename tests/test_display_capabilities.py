from owndash.core.display import DisplayBackend, DisplayCapabilities, DisplayInfo, DisplayProtocolError


class DummyBackend(DisplayBackend):
    def connect(self) -> DisplayInfo:
        return DisplayInfo("dummy", 100, 200)

    def send_jpeg(self, payload: bytes) -> None:
        pass

    def close(self) -> None:
        pass


def test_capabilities_default_to_safe_false_values():
    caps = DisplayCapabilities()
    assert caps.hardware_brightness is False
    assert caps.device_version is False
    assert caps.panel_info is False
    assert caps.expansion_mode is False
    assert caps.startup_image is False
    assert caps.startup_video is False
    assert caps.hardware_screen_off is False
    assert caps.firmware_upgrade is False


def test_optional_controls_fail_safely_by_default():
    backend = DummyBackend()
    assert backend.get_capabilities() == DisplayCapabilities()
    assert backend.get_device_version() is None
    assert backend.get_expansion_mode() is None
    try:
        backend.set_brightness(50)
    except DisplayProtocolError:
        pass
    else:
        raise AssertionError("unsupported brightness must raise DisplayProtocolError")
