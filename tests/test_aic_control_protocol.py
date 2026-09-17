import pytest

from owndash.hardware.aic_protocol import (
    brightness_to_device_value,
    make_control_packet,
    parse_device_version_response,
    parse_panel_info_response,
)


def test_control_packet_layout():
    assert make_control_packet(0x80, b"\x7f") == bytes.fromhex("5a a5 80 00 01 00 00 00 7f")
    assert make_control_packet(0x81, b"\x01") == bytes.fromhex("5a a5 81 00 01 00 00 00 01")
    assert make_control_packet(0x90, b"\x01") == bytes.fromhex("5a a5 90 00 01 00 00 00 01")
    assert make_control_packet(0x91, b"\x01") == bytes.fromhex("5a a5 91 00 01 00 00 00 01")


@pytest.mark.parametrize("percent,expected", [(0, 0), (25, 63), (50, 127), (75, 191), (100, 255)])
def test_brightness_mapping(percent, expected):
    assert brightness_to_device_value(percent) == expected


def test_brightness_rejects_out_of_range():
    with pytest.raises(ValueError):
        brightness_to_device_value(-1)
    with pytest.raises(ValueError):
        brightness_to_device_value(101)


def test_parse_device_version_utf8_payload():
    packet = b"\x5a\xa5\x00\x81\x00" + "1.2.3".encode("utf-8")
    assert parse_device_version_response(packet) == "1.2.3"


def test_parse_panel_info_response():
    packet = bytes([0x5A, 0xA5, 0x00, 0x90, 0, 0, 0, 0, 0x01, 0xE0, 0x07, 0x80, 0x01])
    assert parse_panel_info_response(packet) == (480, 1920, True)


@pytest.mark.parametrize("packet", [b"", b"\x5a\xa5\x00\x81", b"\x00\xa5\x00\x81\x00x"])
def test_parse_device_version_rejects_malformed(packet):
    with pytest.raises(ValueError):
        parse_device_version_response(packet)


def test_parse_panel_info_rejects_short_or_wrong_command():
    with pytest.raises(ValueError):
        parse_panel_info_response(b"\x5a\xa5\x00\x90")
    bad = bytes([0x5A, 0xA5, 0, 0x91, 0, 0, 0, 0, 1, 224, 7, 128, 1])
    with pytest.raises(ValueError):
        parse_panel_info_response(bad)
