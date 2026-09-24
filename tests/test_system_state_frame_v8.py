from owndash.gui.system_state_frame import _portrait_layout


def test_approved_master_geometry_is_v12_contract():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)
    ring_top = layout.hud_center.y() - layout.hud_diameter / 2.0
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert width * 0.65 <= layout.hud_diameter <= width * 0.70
    assert height * 0.16 <= ring_top <= height * 0.21
    assert width * 0.18 <= layout.brand_icon_rect.width() <= width * 0.20
    assert width * 0.085 <= layout.wordmark_font_px <= width * 0.100
    assert layout.status_font_px >= layout.wordmark_font_px
    assert ring_bottom < layout.separator_y


def test_approved_master_keeps_distinct_status_clock_and_floor_zones():
    layout = _portrait_layout(480, 1920)
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()
    assert layout.detail_rect.top() > layout.status_rect.bottom()
    assert layout.bar_rect.top() > layout.detail_rect.bottom()
    assert layout.context_top > layout.bar_rect.bottom()
    assert layout.floor_horizon > layout.context_top
    assert not hasattr(layout, "telemetry_y")
