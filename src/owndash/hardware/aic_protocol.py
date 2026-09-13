from __future__ import annotations

import struct

FRAME_START_MAGIC = 0xA1C62B01
AUTH_DEVICE_MAGIC = 0xA1C62B10
AUTH_HOST_MAGIC = 0xA1C62B11
HEADER_STRUCT = struct.Struct("<IIHHII")


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
