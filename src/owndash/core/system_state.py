from __future__ import annotations

from enum import Enum


class SystemState(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    LOCKED = "locked"
    SUSPENDING = "suspending"
    SHUTTING_DOWN = "shutting_down"
    RESTARTING = "restarting"


_STATE_PRIORITY: dict[SystemState, int] = {
    SystemState.ACTIVE: 0,
    SystemState.IDLE: 10,
    SystemState.LOCKED: 20,
    SystemState.SUSPENDING: 30,
    SystemState.SHUTTING_DOWN: 40,
    SystemState.RESTARTING: 40,
}


def resolve_visible_state(active_states: set[SystemState]) -> SystemState:
    """Return the highest-priority visible state.

    ACTIVE is the derived fallback when no temporary condition is active.
    SHUTTING_DOWN and RESTARTING intentionally share the same priority;
    callers must not assert both simultaneously because logind should surface
    one terminal transition at a time.
    """
    if not active_states:
        return SystemState.ACTIVE
    return max(active_states, key=_STATE_PRIORITY.__getitem__)


class SystemStateCoordinator:
    """Normalize overlapping system conditions into one visible state."""

    __slots__ = ("_active_conditions", "_visible_state")

    def __init__(self) -> None:
        self._active_conditions: set[SystemState] = set()
        self._visible_state = SystemState.ACTIVE

    @property
    def visible_state(self) -> SystemState:
        return self._visible_state

    @property
    def active_conditions(self) -> frozenset[SystemState]:
        return frozenset(self._active_conditions)

    def set_condition(self, state: SystemState, enabled: bool) -> SystemState | None:
        if state is SystemState.ACTIVE:
            raise ValueError("ACTIVE is derived and cannot be set as a condition")

        if enabled:
            self._active_conditions.add(state)
        else:
            self._active_conditions.discard(state)

        visible = resolve_visible_state(self._active_conditions)
        if visible is self._visible_state:
            return None
        self._visible_state = visible
        return visible
