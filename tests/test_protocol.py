import struct

import pytest

from owndash.hardware.aic_protocol import FRAME_START_MAGIC, make_command_header, parse_display_parameters


def test_frame_header_is_exactly_20_bytes_and_little_endian():
    header = make_command_header(FRAME_START_MAGIC, 12345, sequence=7, media_format=2)
    assert len(header) == 20
    magic, length, seq, media_format, reserved, trailer = struct.unpack("<IIHHII", header)
    assert (magic, length, seq, media_format, reserved, trailer) == (
        FRAME_START_MAGIC,
        12345,
        7,
        2,
        0,
        FRAME_START_MAGIC,
    )


def test_display_parameters_are_validated():
    block = struct.pack("<8H", 1, 2, 3, 4, 5, 1920, 480, 60)
    assert parse_display_parameters(block) == (1920, 480, 3, 60)
    with pytest.raises(ValueError):
        parse_display_parameters(b"short")
