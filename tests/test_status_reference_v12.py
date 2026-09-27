from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import _portrait_layout, _portrait_state_copy, render_system_state_image


STRINGS_DE = {
    "standby": "Standby",
    "entering_standby": "Standby wird vorbereitet",
    "system_locked": "System gesperrt",
    "shutting_down": "Herunterfahren",
    "restarting": "Neustart",
    "system_transition": "Systemwechsel",
    "ending_session": "Aktuelle Sitzung wird beendet",
    "idle": "Bereit",
}


def test_approved_reference_places_brand_status_clock_and_floor_in_distinct_zones():
    layout = _portrait_layout(480, 1920)
    ring_top = layout.hud_center.y() - layout.hud_diameter / 2.0
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert 480 * 0.65 <= layout.hud_diameter <= 480 * 0.70
    assert 1920 * 0.16 <= ring_top <= 1920 * 0.21
    assert layout.brand_icon_rect.bottom() < layout.wordmark_rect.top()
    assert layout.wordmark_rect.bottom() < ring_bottom
    assert ring_bottom < layout.separator_y < 1920 * 0.43
    assert 1920 * 0.44 <= layout.state_icon_rect.top() <= 1920 * 0.50
    assert 1920 * 0.51 <= layout.status_rect.top() <= 1920 * 0.57
    assert layout.status_rect.bottom() < layout.detail_rect.top() < layout.bar_rect.top()
    assert 1920 * 0.70 <= layout.context_top <= 1920 * 0.77
    assert 1920 * 0.82 <= layout.floor_horizon <= 1920 * 0.86


def test_approved_reference_brand_is_not_oversized_and_state_remains_dominant():
    layout = _portrait_layout(480, 1920)

    assert 480 * 0.18 <= layout.brand_icon_rect.width() <= 480 * 0.20
    assert 480 * 0.50 <= layout.wordmark_rect.width() <= 480 * 0.60
    assert 480 * 0.085 <= layout.wordmark_font_px <= 480 * 0.100
    assert 480 * 0.62 <= layout.status_rect.width() <= 480 * 0.78
    assert layout.status_font_px >= layout.wordmark_font_px
    assert layout.status_font_px <= 480 * 0.100


def test_long_german_terminal_state_uses_single_reference_headline_copy():
    headline, detail = _portrait_state_copy(SystemState.SHUTTING_DOWN, "Herunterfahren", "")
    assert headline == "HERUNTERFAHREN"
    assert detail == "System wird sicher beendet"

    app = QApplication.instance() or QApplication([])
    image = render_system_state_image(
        480,
        1920,
        SystemState.SHUTTING_DOWN,
        "owndash",
        QIcon(),
        STRINGS_DE,
        clock_text="18:24",
        date_text="21.09.2026",
    )
    assert app is not None
    assert not image.isNull()
    assert image.width() == 480
    assert image.height() == 1920
