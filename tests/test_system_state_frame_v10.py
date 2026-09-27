from PySide6.QtGui import QFontMetricsF, QImage
from PySide6.QtWidgets import QApplication

from owndash.gui.system_state_frame import _fit_single_line_font, _portrait_layout


_APP = QApplication.instance() or QApplication([])


def test_approved_master_keeps_brand_ring_and_status_separate():
    layout = _portrait_layout(480, 1920)
    radius = layout.hud_diameter / 2.0
    hud_bottom = layout.hud_center.y() + radius

    assert hud_bottom < layout.separator_y
    assert layout.brand_icon_rect.bottom() < layout.wordmark_rect.top()
    assert layout.wordmark_rect.bottom() < hud_bottom
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()


def test_approved_master_long_terminal_headline_fits_safe_width():
    layout = _portrait_layout(480, 1920)
    image = QImage(480, 1920, QImage.Format_RGB32)
    title = "HERUNTERFAHREN"
    safe_rect = layout.status_rect.adjusted(14, 0, -14, 0)
    font = _fit_single_line_font(image, title, safe_rect, layout.status_font_px, bold=False)
    metrics = QFontMetricsF(font)

    assert layout.status_font_px <= 480 * 0.100
    assert safe_rect.left() >= 480 * 0.08
    assert safe_rect.right() <= 480 * 0.92
    assert metrics.horizontalAdvance(title) <= safe_rect.width()


def test_approved_master_footer_is_separate_below_status_and_context():
    layout = _portrait_layout(480, 1920)
    assert 1920 * 0.70 <= layout.context_top <= 1920 * 0.77
    assert 1920 * 0.82 <= layout.floor_horizon <= 1920 * 0.86
    assert layout.status_rect.bottom() < layout.detail_rect.top()
    assert layout.bar_rect.bottom() < layout.context_top
    assert not hasattr(layout, "status_panel_rect")
