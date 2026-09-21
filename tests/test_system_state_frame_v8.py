from __future__ import annotations

from owndash.gui.system_state_frame import _portrait_layout


def test_v9_portrait_branding_is_present_without_colliding_with_status():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert width * 0.72 <= layout.hud_diameter <= width * 0.78
    assert layout.brand_icon_rect.width() >= width * 0.18
    assert width * 0.12 <= layout.wordmark_font_px <= width * 0.13
    assert layout.status_font_px >= layout.wordmark_font_px * 1.05


def test_v9_portrait_composition_has_clear_brand_status_context_zones():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert layout.hud_center.y() <= height * 0.21
    assert layout.status_rect.top() >= height * 0.50
    assert layout.bar_rect.bottom() <= height * 0.66
    assert layout.context_top >= height * 0.70
    assert layout.floor_horizon >= height * 0.88


def test_v9_portrait_layout_keeps_telemetry_tick_band_removed():
    layout = _portrait_layout(480, 1920)

    assert not hasattr(layout, "telemetry_y")
