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

# Distinctive neon landmarks sampled from the user-approved 480x1920
# GESPERRT reference. Keeping these in the regression suite makes the visual
# design an explicit contract instead of merely checking that "some HUD"
# rendered successfully.
_APPROVED_LOCKED_LANDMARKS = [
    (36, 18, 0, 162, 236),
    (444, 18, 141, 42, 236),
    (48, 108, 21, 149, 220),
    (24, 162, 0, 190, 206),
    (456, 162, 255, 101, 255),
    (240, 234, 80, 136, 253),
    (456, 234, 253, 108, 254),
    (204, 252, 70, 147, 249),
    (276, 252, 100, 105, 252),
    (24, 324, 71, 210, 236),
    (456, 360, 212, 10, 237),
    (216, 378, 0, 213, 249),
    (312, 378, 242, 109, 250),
    (456, 414, 250, 17, 255),
    (12, 450, 0, 233, 255),
    (240, 450, 1, 118, 205),
    (204, 558, 0, 187, 252),
    (276, 558, 102, 102, 251),
    (168, 594, 76, 253, 255),
    (312, 594, 244, 63, 254),
    (360, 594, 247, 41, 244),
    (84, 630, 28, 192, 211),
    (132, 630, 67, 247, 255),
    (396, 630, 251, 71, 254),
    (228, 648, 1, 192, 253),
    (48, 666, 0, 166, 197),
    (96, 684, 1, 251, 255),
    (168, 684, 34, 223, 252),
    (312, 684, 157, 42, 251),
    (384, 684, 254, 89, 252),
    (72, 738, 6, 255, 255),
    (144, 738, 31, 179, 246),
    (396, 738, 253, 34, 252),
    (72, 828, 1, 248, 255),
    (144, 828, 0, 187, 245),
    (336, 828, 238, 0, 237),
    (396, 828, 254, 13, 253),
    (96, 882, 0, 230, 253),
    (168, 882, 17, 213, 244),
    (384, 882, 254, 36, 252),
    (60, 918, 9, 108, 217),
    (420, 918, 168, 2, 222),
    (156, 936, 1, 229, 243),
    (108, 954, 2, 175, 231),
    (372, 954, 247, 22, 255),
    (180, 972, 3, 230, 255),
    (312, 972, 215, 71, 253),
    (216, 990, 48, 184, 251),
    (276, 990, 128, 99, 253),
    (228, 1062, 0, 164, 253),
    (24, 1116, 3, 124, 200),
    (456, 1116, 160, 18, 216),
    (48, 1314, 51, 188, 246),
    (432, 1314, 214, 0, 249),
    (432, 1368, 155, 0, 217),
    (156, 1548, 0, 244, 254),
    (240, 1548, 14, 219, 252),
    (324, 1548, 0, 215, 247),
    (48, 1602, 0, 191, 252),
    (432, 1602, 173, 29, 249),
    (48, 1674, 1, 171, 250),
    (240, 1674, 18, 194, 249),
    (360, 1674, 0, 67, 226),
    (432, 1674, 146, 45, 250),
    (132, 1710, 0, 170, 250),
    (48, 1746, 2, 197, 248),
    (240, 1746, 77, 244, 253),
    (348, 1746, 165, 18, 247),
    (132, 1764, 1, 110, 206),
    (108, 1818, 64, 185, 241),
    (372, 1818, 228, 50, 233),
    (36, 1854, 2, 139, 220),
]


def _digest(image):
    return bytes(image.constBits())


def _landmark_rgb_error(image) -> float:
    total = 0
    channels = 0
    for x, y, red, green, blue in _APPROVED_LOCKED_LANDMARKS:
        actual = image.pixelColor(x, y)
        total += abs(actual.red() - red)
        total += abs(actual.green() - green)
        total += abs(actual.blue() - blue)
        channels += 3
    return total / channels


def test_locked_portrait_matches_approved_golden_reference():
    frame = render_system_state_image(
        480, 1920, SystemState.LOCKED, "owndash", QIcon(), STRINGS,
        clock_text="18:24", date_text="21.09.2026", animation_phase=0.0,
    )

    # Reject simplified or alternate HUDs. The approved design has dense
    # cyan/magenta perimeter rails, the multi-layer ring and illuminated floor.
    assert _landmark_rgb_error(frame) < 18.0


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
