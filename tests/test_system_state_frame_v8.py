from __future__ import annotations

from owndash.gui.system_state_frame import _portrait_layout


def test_v10_portrait_branding_is_present_without_colliding_with_status():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert width * 0.82 <= layout.hud_diameter <= width * 0.86
    assert layout.brand_icon_rect.width() >= width * 0.18
    assert width * 0.12 <= layout.wordmark_font_px <= width * 0.13
    assert layout.status_font_px < layout.wordmark_font_px


def test_v10_portrait_composition_has_clear_brand_status_context_zones():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert height * 0.24 <= layout.hud_center.y() <= height * 0.26
    assert layout.status_rect.top() < height * 0.40
    assert layout.bar_rect.bottom() <= height * 0.33
    assert layout.context_top >= height * 0.72
    assert layout.floor_horizon >= height * 0.86


def test_v9_portrait_layout_keeps_telemetry_tick_band_removed():
    layout = _portrait_layout(480, 1920)

    assert not hasattr(layout, "telemetry_y")
