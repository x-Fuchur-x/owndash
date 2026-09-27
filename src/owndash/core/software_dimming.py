from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageEnhance


def clamp_software_dimming(percent: int | float) -> int:
    """Clamp OwnDash software dimming to the safe user-facing range."""
    try:
        value = int(percent)
    except (TypeError, ValueError, OverflowError):
        value = 100
    return max(10, min(100, value))


def dim_jpeg(payload: bytes, percent: int | float) -> bytes:
    """Return a visually dimmed JPEG without touching display hardware.

    100% intentionally returns the original bytes unchanged, so the default
    path keeps its existing performance, caching behavior and image quality.
    """
    level = clamp_software_dimming(percent)
    if level >= 100:
        return payload

    with Image.open(BytesIO(payload)) as source:
        rgb = source.convert("RGB")
        dimmed = ImageEnhance.Brightness(rgb).enhance(level / 100.0)
        output = BytesIO()
        dimmed.save(output, format="JPEG", quality=92, optimize=False)
        return output.getvalue()
