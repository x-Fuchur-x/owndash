from __future__ import annotations

from owndash.gui.system_state_frame import _portrait_layout


def test_v11_portrait_branding_matches_approved_reference_proportions():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert width * 0.84 <= layout.hud_diameter <= width * 0.90
    assert layout.brand_icon_rect.width() >= width * 0.18
    assert width * 0.12 <= layout.wordmark_font_px <= width * 0.14
    assert layout.status_font_px < layout.wordmark_font_px


def test_v11_portrait_composition_has_brand_status_context_footer_zones():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert height * 0.22 <= layout.hud_center.y() <= height * 0.25
    assert layout.separator_y > ring_bottom
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()
    assert layout.detail_rect.top() > layout.status_rect.bottom()
    assert layout.bar_rect.top() > layout.detail_rect.bottom()
    assert layout.context_top >= height * 0.65
    assert layout.floor_horizon >= height * 0.86


def test_v11_portrait_layout_keeps_telemetry_tick_band_removed():
    layout = _portrait_layout(480, 1920)
    assert not hasattr(layout, "telemetry_y")
