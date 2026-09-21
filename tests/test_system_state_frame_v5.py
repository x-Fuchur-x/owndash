import math

from owndash.gui.system_state_frame import _portrait_brand_icon_rect, _portrait_layout


def test_v10_brand_icon_is_visible_above_wordmark_inside_ring():
    layout = _portrait_layout(480, 1920)
    icon_rect = _portrait_brand_icon_rect(layout)
    radius = layout.hud_diameter / 2.0

    assert icon_rect.width() >= 480 * 0.09
    assert icon_rect.height() == icon_rect.width()
    assert icon_rect.center().x() == layout.hud_center.x()
    assert icon_rect.bottom() < layout.wordmark_rect.top()
    assert math.hypot(
        icon_rect.center().x() - layout.hud_center.x(),
        icon_rect.center().y() - layout.hud_center.y(),
    ) + icon_rect.width() / 2.0 < radius * 0.82
