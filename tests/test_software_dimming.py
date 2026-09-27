from __future__ import annotations

from importlib import import_module
from io import BytesIO
from pathlib import Path

from PIL import Image

from owndash.core.preferences import AppPreferences


def _jpeg(rgb: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (8, 8), rgb)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def _pixel(payload: bytes) -> tuple[int, int, int]:
    with Image.open(BytesIO(payload)) as image:
        return tuple(image.convert("RGB").getpixel((4, 4)))


def test_preferences_default_and_clamp_software_dimming():
    assert AppPreferences().software_dimming_percent == 100
    assert AppPreferences.from_raw({"software_dimming_percent": 5}).software_dimming_percent == 10
    assert AppPreferences.from_raw({"software_dimming_percent": 150}).software_dimming_percent == 100
    assert AppPreferences.from_raw({"software_dimming_percent": "50"}).software_dimming_percent == 50


def test_dim_jpeg_is_noop_at_100_and_darkens_at_50():
    module = import_module("owndash.core.software_dimming")
    dim_jpeg = module.dim_jpeg
    original = _jpeg((240, 200, 160))

    assert dim_jpeg(original, 100) is original

    dimmed = dim_jpeg(original, 50)
    original_pixel = _pixel(original)
    dimmed_pixel = _pixel(dimmed)
    for original_channel, dimmed_channel in zip(original_pixel, dimmed_pixel):
        assert abs(dimmed_channel - round(original_channel * 0.5)) <= 8


def test_dim_jpeg_clamps_to_safe_ui_range():
    module = import_module("owndash.core.software_dimming")
    dim_jpeg = module.dim_jpeg
    original = _jpeg((200, 200, 200))

    below_minimum = _pixel(dim_jpeg(original, 0))[0]
    at_minimum = _pixel(dim_jpeg(original, 10))[0]
    above_maximum = dim_jpeg(original, 500)

    assert abs(below_minimum - at_minimum) <= 3
    assert above_maximum is original


def test_software_dimming_hint_reserves_two_text_lines():
    source = Path("src/owndash/gui/device_center_window.py").read_text(encoding="utf-8")

    assert "hint.setWordWrap(True)" in source
    assert "hint.setMinimumHeight(hint.fontMetrics().lineSpacing() * 2 + 8)" in source
