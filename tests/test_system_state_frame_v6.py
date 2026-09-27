from PySide6.QtGui import QIcon

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import render_system_state_image


STRINGS = {
    "standby": "Standby",
    "entering_standby": "Entering standby",
    "system_locked": "System locked",
    "shutting_down": "Shutting down",
    "restarting": "Restarting",
    "idle": "Idle",
}


def _render(phase: float):
    return render_system_state_image(
        480,
        1920,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        STRINGS,
        animation_phase=phase,
    )


def test_approved_locked_master_keeps_live_animation_cue():
    phase_a = _render(0.0)
    phase_b = _render(0.5)

    assert phase_a.size().width() == 480
    assert phase_a.size().height() == 1920
    assert phase_b.size() == phase_a.size()
    assert bytes(phase_a.constBits()) != bytes(phase_b.constBits())
