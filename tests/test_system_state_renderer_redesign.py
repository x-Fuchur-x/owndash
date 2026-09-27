from pathlib import Path

from PySide6.QtGui import QIcon

from owndash.core.system_state import SystemState
from owndash.gui.shutdown_frame import render_shutdown_image
from owndash.gui.system_state_frame import render_system_state_image


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


def _digest(image):
    return bytes(image.constBits())


def test_system_state_renderer_no_longer_depends_on_embedded_master_artwork():
    gui_dir = Path(__file__).resolve().parents[1] / "src" / "owndash" / "gui"
    source = (gui_dir / "system_state_frame.py").read_text(encoding="utf-8")

    assert "status_master" not in source
    assert not (gui_dir / "status_master.py").exists()
    assert list(gui_dir.glob("_status_master_data_*.py")) == []


def test_disconnected_shutdown_screen_uses_the_same_visual_renderer_family():
    source = Path(render_shutdown_image.__code__.co_filename).read_text(encoding="utf-8")
    assert "render_disconnected_status_image" in source


def test_persistent_ring_animation_changes_locked_and_idle_frames():
    for state in (SystemState.LOCKED, SystemState.IDLE):
        frame_a = render_system_state_image(
            480, 1920, state, "owndash", QIcon(), STRINGS,
            clock_text="17:42", date_text="27.09.2026", animation_phase=0.0,
        )
        frame_b = render_system_state_image(
            480, 1920, state, "owndash", QIcon(), STRINGS,
            clock_text="17:42", date_text="27.09.2026", animation_phase=0.5,
        )
        assert _digest(frame_a) != _digest(frame_b)


def test_terminal_frames_remain_static_for_lifecycle_safety():
    for state in (SystemState.SUSPENDING, SystemState.SHUTTING_DOWN, SystemState.RESTARTING):
        frame_a = render_system_state_image(
            480, 1920, state, "owndash", QIcon(), STRINGS, animation_phase=0.0,
        )
        frame_b = render_system_state_image(
            480, 1920, state, "owndash", QIcon(), STRINGS, animation_phase=0.7,
        )
        assert _digest(frame_a) == _digest(frame_b)
