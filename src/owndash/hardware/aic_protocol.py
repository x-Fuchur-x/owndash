from __future__ import annotations

import struct

FRAME_START_MAGIC = 0xA1C62B01
AUTH_DEVICE_MAGIC = 0xA1C62B10
AUTH_HOST_MAGIC = 0xA1C62B11
HEADER_STRUCT = struct.Struct("<IIHHII")
CONTROL_PREFIX = b"\x5a\xa5"


def make_command_header(magic: int, payload_length: int, sequence: int = 0, media_format: int = 0) -> bytes:
    """Build the 20-byte little-endian command header used by compatible displays."""
    if not 0 <= payload_length <= 0xFFFFFFFF:
        raise ValueError("payload_length out of range")
    return HEADER_STRUCT.pack(
        magic & 0xFFFFFFFF,
        payload_length,
        sequence & 0xFFFF,
        media_format & 0xFFFF,
        0,
        magic & 0xFFFFFFFF,
    )


def parse_display_parameters(data: bytes) -> tuple[int, int, int, int]:
    """Return width, height, media format and fps from a display parameter block."""
    if len(data) < 16:
        raise ValueError("display parameter block is too short")
    _version, _chip, media_format, _bus, _modes, width, height, fps = struct.unpack_from("<8H", data, 0)
    if width <= 0 or height <= 0:
        raise ValueError("display reported an invalid resolution")
    return width, height, media_format, fps


def make_control_packet(command: int, payload: bytes = b"") -> bytes:
    """Build a verified 5A A5 ArtInChip control packet."""
    if not 0 <= command <= 0xFF:
        raise ValueError("command out of range")
    return CONTROL_PREFIX + bytes((command, 0)) + struct.pack("<I", len(payload)) + payload


def brightness_to_device_value(percent: int) -> int:
    """Map a 0-100 UI brightness percentage to the device's 0-255 byte range."""
    if not 0 <= percent <= 100:
        raise ValueError("brightness percent out of range")
    return (percent * 255) // 100


def _validate_control_response(data: bytes, command: int, minimum_length: int) -> None:
    if len(data) < minimum_length:
        raise ValueError("control response is too short")
    if data[:2] != CONTROL_PREFIX:
        raise ValueError("invalid control response prefix")
    if data[3] != command:
        raise ValueError("unexpected control response command")


def parse_device_version_response(data: bytes) -> str:
    """Decode the verified UTF-8 device-version response payload."""
    _validate_control_response(data, 0x81, 5)
    try:
        return data[5:].decode("utf-8").rstrip("\x00")
    except UnicodeDecodeError as exc:
        raise ValueError("device version is not valid UTF-8") from exc


def parse_panel_info_response(data: bytes) -> tuple[int, int, bool]:
    """Return native width, height and Expansion Screen Mode state."""
    _validate_control_response(data, 0x90, 13)
    width = int.from_bytes(data[8:10], "big")
    height = int.from_bytes(data[10:12], "big")
    if width <= 0 or height <= 0:
        raise ValueError("panel response contains invalid dimensions")
    return width, height, bool(data[12])
