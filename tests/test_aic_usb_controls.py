from __future__ import annotations

from owndash.hardware.aic_usb import AicUsbDisplayBackend, EP_IN, EP_OUT


class FakeUsbDevice:
    def __init__(self, responses: list[bytes] | None = None):
        self.responses = list(responses or [])
        self.writes: list[tuple[int, bytes, int]] = []
        self.reads: list[tuple[int, int, int]] = []

    def write(self, endpoint: int, payload: bytes, timeout: int = 5000) -> int:
        data = bytes(payload)
        self.writes.append((endpoint, data, timeout))
        return len(data)

    def read(self, endpoint: int, size: int, timeout: int = 5000) -> bytes:
        self.reads.append((endpoint, size, timeout))
        return self.responses.pop(0)


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


def test_set_brightness_uses_existing_vendor_bulk_interface():
    backend = AicUsbDisplayBackend()
    device = FakeUsbDevice()
    backend._dev = device

    backend.set_brightness(50)

    assert device.writes == [
        (EP_OUT, bytes.fromhex("5a a5 80 00 01 00 00 00 7f"), 5000),
    ]


def test_get_device_version_queries_existing_vendor_bulk_interface_and_caches():
    backend = AicUsbDisplayBackend()
    device = FakeUsbDevice([b"\x5a\xa5\x00\x81\x00" + b"1.2.3"])
    backend._dev = device

    assert backend.get_device_version() == "1.2.3"
    assert backend.get_device_version() == "1.2.3"
    assert device.writes == [
        (EP_OUT, bytes.fromhex("5a a5 81 00 01 00 00 00 01"), 5000),
    ]
    assert device.reads == [(EP_IN, 4096, 1000)]


def test_expansion_mode_round_trip_uses_vendor_bulk_panel_info_query():
    backend = AicUsbDisplayBackend()
    panel_on = bytes([0x5A, 0xA5, 0x00, 0x90, 0, 0, 0, 0, 0x01, 0xE0, 0x07, 0x80, 0x01])
    device = FakeUsbDevice([panel_on])
    backend._dev = device

    backend.set_expansion_mode(True)

    assert device.writes == [
        (EP_OUT, bytes.fromhex("5a a5 91 00 01 00 00 00 01"), 5000),
        (EP_OUT, bytes.fromhex("5a a5 90 00 01 00 00 00 01"), 5000),
    ]
    assert device.reads == [(EP_IN, 4096, 1000)]
    assert backend.get_expansion_mode() is True
