from __future__ import annotations

from owndash.gui.system_state_frame import _portrait_layout


def test_v8_portrait_branding_is_more_present_but_status_stays_primary():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert layout.hud_diameter <= width * 0.70
    assert layout.brand_icon_rect.width() >= width * 0.18
    assert layout.wordmark_font_px >= width * 0.14
    assert layout.status_font_px >= layout.wordmark_font_px * 1.05


def test_v8_portrait_composition_has_clear_brand_status_context_zones():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert layout.hud_center.y() <= height * 0.20
    assert layout.status_rect.top() >= height * 0.36
    assert layout.bar_rect.bottom() <= height * 0.56
    assert layout.context_top >= height * 0.62
    assert layout.floor_horizon >= height * 0.84


def test_v8_portrait_layout_drops_decorative_telemetry_tick_band():
    layout = _portrait_layout(480, 1920)

    assert not hasattr(layout, "telemetry_y")
