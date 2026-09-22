from importlib.resources import files

from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QApplication

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import render_system_state_image


STRINGS_DE = {
    "system_locked": "System gesperrt",
    "idle": "Bereit",
    "standby": "Standby",
    "entering_standby": "Standby wird vorbereitet",
    "system_transition": "Systemwechsel",
    "ending_session": "Aktuelle Sitzung wird beendet",
    "shutting_down": "Herunterfahren",
    "restarting": "Neustart",
}


def test_locked_panel_uses_approved_master_artwork():
    app = QApplication.instance() or QApplication([])
    resource = files("owndash").joinpath("assets", "status-master-locked-480x1920.jpg")
    assert resource.is_file(), "approved status master must be packaged"

    master = QImage.fromData(resource.read_bytes(), "JPG")
    assert (master.width(), master.height()) == (480, 1920)

    rendered = render_system_state_image(
        480,
        1920,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        STRINGS_DE,
        clock_text="23:59",
        date_text="22.09.2026",
        animation_phase=0.31,
    )
    assert app is not None
    assert (rendered.width(), rendered.height()) == (480, 1920)

    for x, y in ((240, 330), (240, 475), (95, 840), (240, 1505), (300, 1810)):
        assert rendered.pixelColor(x, y) == master.pixelColor(x, y)

    clock_changed = any(
        rendered.pixelColor(x, y) != master.pixelColor(x, y)
        for y in range(1120, 1190, 4)
        for x in range(150, 330, 4)
    )
    assert clock_changed
