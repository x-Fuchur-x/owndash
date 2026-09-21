from PySide6.QtGui import QFontMetricsF, QImage

from owndash.gui.system_state_frame import _fit_single_line_font, _portrait_layout


def test_v10_keeps_brand_and_status_inside_one_compact_hero_hud():
    layout = _portrait_layout(480, 1920)
    radius = layout.hud_diameter / 2.0
    hud_top = layout.hud_center.y() - radius
    hud_bottom = layout.hud_center.y() + radius

    assert 1920 * 0.11 <= hud_top <= 1920 * 0.18
    assert hud_bottom <= 1920 * 0.50
    assert layout.brand_icon_rect.top() > hud_top
    assert layout.wordmark_rect.top() > layout.brand_icon_rect.bottom()
    assert layout.status_rect.top() > layout.wordmark_rect.bottom()
    assert layout.status_rect.bottom() < hud_bottom


def test_v10_status_is_refined_single_line_not_old_block_headline():
    layout = _portrait_layout(480, 1920)
    image = QImage(480, 1920, QImage.Format_RGB32)
    title = "System wird heruntergefahren"
    font = _fit_single_line_font(image, title, layout.status_rect, layout.status_font_px, bold=False)
    metrics = QFontMetricsF(font)

    assert layout.status_font_px <= 480 * 0.075
    assert layout.status_rect.width() >= 480 * 0.72
    assert metrics.horizontalAdvance(title) <= layout.status_rect.width()


def test_v10_footer_is_separate_and_old_tall_status_panel_is_gone():
    layout = _portrait_layout(480, 1920)

    assert layout.context_top >= 1920 * 0.72
    assert layout.floor_horizon >= 1920 * 0.86
    assert not hasattr(layout, "status_panel_rect")
    assert not hasattr(layout, "status_icon_rect")
