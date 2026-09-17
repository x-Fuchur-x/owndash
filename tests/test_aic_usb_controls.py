from __future__ import annotations

from owndash.hardware.aic_usb import AicUsbDisplayBackend


class FakeControl:
    def __init__(self, responses: list[bytes] | None = None):
        self.responses = list(responses or [])
        self.writes: list[bytes] = []
        self.is_open = True

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def write(self, payload: bytes) -> None:
        self.writes.append(payload)

    def read_response(self, expected_command: int, minimum_length: int, timeout: float = 1.0) -> bytes:
        response = self.responses.pop(0)
        assert response[3] == expected_command
        assert len(response) >= minimum_length
        return response


def test_supported_device_capabilities_are_conservative():
    backend = AicUsbDisplayBackend()
    caps = backend.get_capabilities()
    assert caps.hardware_brightness is True
    assert caps.device_version is True
    assert caps.panel_info is True
    assert caps.expansion_mode is True
    assert caps.startup_image is False
    assert caps.startup_video is False
    assert caps.hardware_screen_off is False
    assert caps.firmware_upgrade is False


def test_set_brightness_emits_verified_packet():
    backend = AicUsbDisplayBackend()
    control = FakeControl()
    backend._control = control
    backend.set_brightness(50)
    assert control.writes == [bytes.fromhex("5a a5 80 00 01 00 00 00 7f")]


def test_get_device_version_queries_and_caches_utf8_response():
    backend = AicUsbDisplayBackend()
    control = FakeControl([b"\x5a\xa5\x00\x81\x00" + b"1.2.3"])
    backend._control = control
    assert backend.get_device_version() == "1.2.3"
    assert control.writes == [bytes.fromhex("5a a5 81 00 01 00 00 00 01")]


def test_expansion_mode_round_trip_uses_panel_info_query():
    backend = AicUsbDisplayBackend()
    panel_on = bytes([0x5A, 0xA5, 0x00, 0x90, 0, 0, 0, 0, 0x01, 0xE0, 0x07, 0x80, 0x01])
    control = FakeControl([panel_on])
    backend._control = control
    backend.set_expansion_mode(True)
    assert control.writes == [
        bytes.fromhex("5a a5 91 00 01 00 00 00 01"),
        bytes.fromhex("5a a5 90 00 01 00 00 00 01"),
    ]
    assert backend.get_expansion_mode() is True
