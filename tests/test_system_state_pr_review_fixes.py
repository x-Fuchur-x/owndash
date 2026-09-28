from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from PySide6.QtGui import QColor, QIcon

from owndash.core.preferences import AppPreferences
from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import render_system_state_image
from owndash.gui.system_state_settings import SystemStateSettingsWidget


DE_STRINGS = {
    "idle": "Ruhemodus",
    "system_locked": "System gesperrt",
    "standby": "Standby",
    "entering_standby": "Standby wird vorbereitet",
    "system_transition": "Systemwechsel",
    "ending_session": "OwnDash beendet die aktuelle Sitzung.",
    "shutting_down": "Herunterfahren",
    "restarting": "Neustart",
}

EN_STRINGS = {
    "idle": "Idle",
    "system_locked": "System locked",
    "standby": "Standby",
    "entering_standby": "Entering standby",
    "system_transition": "System transition",
    "ending_session": "OwnDash is ending the current session.",
    "shutting_down": "Shutting down",
    "restarting": "Restarting",
}


def _digest(image) -> bytes:
    return bytes(image.constBits())


def test_state_copy_is_rendered_from_localized_strings():
    german = render_system_state_image(
        480,
        1920,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        DE_STRINGS,
        clock_text="21:33",
        date_text="28.09.2026",
    )
    english = render_system_state_image(
        480,
        1920,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        EN_STRINGS,
        clock_text="21:33",
        date_text="2026-09-28",
    )

    assert _digest(german) != _digest(english)


def test_landscape_contains_portrait_artwork_without_stretching():
    image = render_system_state_image(
        1920,
        480,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        EN_STRINGS,
    )
    background = QColor("#020711")

    # A 480x1920 source contained in 1920x480 is 120 px wide and centered.
    assert image.pixelColor(890, 240) == background
    assert image.pixelColor(1030, 240) == background
    assert image.pixelColor(960, 240) != background


def test_settings_hide_nonfunctional_theme_selector_and_keep_saved_value():
    prefs = AppPreferences(system_state_theme="bazzite-inspired")
    widget = SystemStateSettingsWidget(prefs)
    try:
        assert not hasattr(widget, "theme_combo")
        widget.apply_to(prefs)
        assert prefs.system_state_theme == "bazzite-inspired"
    finally:
        widget.deleteLater()


def test_retired_master_artifacts_are_absent():
    assert not files("owndash").joinpath("assets", "status_hud_master.jpg").is_file()
    gui_dir = Path(render_system_state_image.__code__.co_filename).parent
    assert not (gui_dir / "_locked_golden_data_00.py").exists()
