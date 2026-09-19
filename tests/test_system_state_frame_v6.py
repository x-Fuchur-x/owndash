import math

from PySide6.QtGui import QIcon

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import _portrait_layout, render_system_state_image


# V6 physical-display regression checks intentionally sample the 480×1920
# composition used by the real VSDISPLAY panel.
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


def _point(center, radius: float, degrees: float) -> tuple[int, int]:
    angle = math.radians(degrees)
    return (
        round(center.x() + math.cos(angle) * radius),
        round(center.y() + math.sin(angle) * radius),
    )


def _is_neon(image, x: int, y: int) -> bool:
    # Small local tolerance keeps this about visible continuity rather than
    # one exact antialiasing pixel.
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            c = image.pixelColor(x + dx, y + dy)
            hi = max(c.red(), c.green(), c.blue())
            lo = min(c.red(), c.green(), c.blue())
            if hi >= 105 and hi - lo >= 42:
                return True
    return False


def test_v6_rail_ring_junctions_have_phase_independent_bridge_segments():
    layout = _portrait_layout(480, 1920)
    ring_radius = layout.hud_diameter * 0.494

    # The rails dock at these four angles. A permanent short ring bridge must
    # surround every dock so animated segmented-ring gaps can never make the
    # connection look broken on the physical display.
    for phase in (0.0, 0.5):
        image = _render(phase)
        for dock_angle in (35.0, 145.0, 215.0, 325.0):
            for offset in (-6.0, -3.0, 0.0, 3.0, 6.0):
                x, y = _point(layout.hud_center, ring_radius, dock_angle + offset)
                assert _is_neon(image, x, y), (
                    f"missing visible ring bridge at phase={phase}, "
                    f"dock={dock_angle}, offset={offset}"
                )
