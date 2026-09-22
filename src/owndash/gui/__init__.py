"""OwnDash GUI package initialization."""
from __future__ import annotations

# Keep the general resolution-independent renderer for every state/display,
# but route the approved physical 480x1920 locked panel through the exact
# raster master. Patching here keeps all existing imports of
# ``owndash.gui.system_state_frame.render_system_state_image`` compatible.
from . import system_state_frame as _system_state_frame
from .status_master import render_locked_master as _render_locked_master
from owndash.core.system_state import SystemState


_procedural_system_state_renderer = _system_state_frame.render_system_state_image


def _render_system_state_with_approved_master(
    width: int,
    height: int,
    state: SystemState,
    theme: str,
    icon,
    strings: dict[str, str],
    *,
    clock_text: str | None = None,
    date_text: str | None = None,
    sensor_text: str | None = None,
    animation_phase: float = 0.0,
):
    if (
        int(width) == 480
        and int(height) == 1920
        and state is SystemState.LOCKED
        and str(theme) == "owndash"
    ):
        return _render_locked_master(clock_text, date_text, animation_phase)
    return _procedural_system_state_renderer(
        width,
        height,
        state,
        theme,
        icon,
        strings,
        clock_text=clock_text,
        date_text=date_text,
        sensor_text=sensor_text,
        animation_phase=animation_phase,
    )


_system_state_frame.render_system_state_image = _render_system_state_with_approved_master
