from PySide6.QtCore import QRectF
from PySide6.QtGui import QFontMetricsF, QIcon, QImage

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import _fit_single_line_font, _portrait_layout, render_system_state_image


STRINGS = {
    "standby": "Standby",
    "entering_standby": "Standby wird vorbereitet",
    "system_locked": "System gesperrt",
    "shutting_down": "Herunterfahren",
    "restarting": "Neustart",
    "system_transition": "Systemwechsel",
    "ending_session": "OwnDash beendet die aktuelle Sitzung.",
    "idle": "Ruhemodus",
}


def _render(state: SystemState, *, icon: QIcon | None = None) -> QImage:
    return render_system_state_image(
        480,
        1920,
        state,
        "owndash",
        icon or QIcon(),
        STRINGS,
        clock_text="18:24",
        date_text="21.09.2026",
        animation_phase=0.25,
    )


def test_v10_portrait_uses_compact_hero_and_separate_context_zone():
    layout = _portrait_layout(480, 1920)

    # The approved v9 composition leaves the top third to the OwnDash ring,
    # then places the status block clearly below it instead of crowding it.
    assert layout.status_rect.top() < 1920 * 0.40
    assert layout.context_top >= 1920 * 0.70
    assert layout.status_rect.bottom() < layout.context_top


def test_v10_long_terminal_title_fits_status_width_without_touching_edges():
    layout = _portrait_layout(480, 1920)
    safe_rect = layout.status_rect.adjusted(14, 0, -14, 0)
    title = "HERUNTERFAHREN"
    font = _fit_single_line_font(QImage(480, 1920, QImage.Format_RGB32), title, safe_rect, layout.status_font_px, bold=False)
    metrics = QFontMetricsF(font)

    assert metrics.horizontalAdvance(title) <= safe_rect.width()
    assert safe_rect.left() >= 480 * 0.08
    assert safe_rect.right() <= 480 * 0.92


def test_v10_every_supported_state_still_renders_at_native_portrait_size():
    for state in (
        SystemState.IDLE,
        SystemState.LOCKED,
        SystemState.SUSPENDING,
        SystemState.TRANSITIONING,
        SystemState.SHUTTING_DOWN,
        SystemState.RESTARTING,
    ):
        image = _render(state)
        assert image.size().width() == 480
        assert image.size().height() == 1920
        assert not image.isNull()
