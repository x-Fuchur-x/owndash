from PySide6.QtGui import QIcon

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import (
    render_disconnected_status_image,
    render_system_state_image,
)


STRINGS = {
    "standby": "Standby",
    "entering_standby": "Entering standby",
    "system_locked": "System locked",
    "shutting_down": "Shutting down",
    "restarting": "Restarting",
    "system_transition": "System transition",
    "ending_session": "OwnDash is ending the current session.",
    "idle": "Idle",
}


def _digest(image) -> bytes:
    return bytes(image.constBits())


def _render(state: SystemState, *, clock_text: str | None, date_text: str | None):
    return render_system_state_image(
        1024,
        600,
        state,
        "owndash",
        QIcon(),
        STRINGS,
        clock_text=clock_text,
        date_text=date_text,
        animation_phase=0.0,
    )


def test_static_lifecycle_states_ignore_clock_and_date_inputs():
    for state in (
        SystemState.SUSPENDING,
        SystemState.TRANSITIONING,
        SystemState.SHUTTING_DOWN,
        SystemState.RESTARTING,
    ):
        early = _render(state, clock_text="10:15", date_text="30.09.2026")
        late = _render(state, clock_text="23:58", date_text="01.10.2026")
        assert _digest(early) == _digest(late)


def test_disconnected_screen_never_depends_on_clock_or_date():
    early = render_disconnected_status_image(
        1024,
        600,
        QIcon(),
        clock_text="10:15",
        date_text="30.09.2026",
    )
    late = render_disconnected_status_image(
        1024,
        600,
        QIcon(),
        clock_text="23:58",
        date_text="01.10.2026",
    )
    assert _digest(early) == _digest(late)


def test_idle_keeps_live_clock_but_ignores_date():
    early = _render(SystemState.IDLE, clock_text="10:15", date_text="30.09.2026")
    late_clock = _render(SystemState.IDLE, clock_text="10:16", date_text="30.09.2026")
    later_date = _render(SystemState.IDLE, clock_text="10:15", date_text="01.10.2026")

    assert _digest(early) != _digest(late_clock)
    assert _digest(early) == _digest(later_date)


def test_locked_keeps_live_clock_and_date():
    early = _render(SystemState.LOCKED, clock_text="10:15", date_text="30.09.2026")
    later = _render(SystemState.LOCKED, clock_text="10:16", date_text="01.10.2026")
    assert _digest(early) != _digest(later)
