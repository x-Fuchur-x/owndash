from __future__ import annotations

from collections.abc import Callable

from owndash.core.system_state import SystemState, SystemStateCoordinator


class SystemStateRuntime:
    """Apply system-state policy and emit only visible display transitions.

    The runtime is intentionally UI-agnostic. It keeps track of overlapping
    conditions (idle, lock, suspend, shutdown/restart), resolves their priority
    through ``SystemStateCoordinator`` and invokes exactly one callback when the
    visible state changes. Returning to ACTIVE restores the normal dashboard.
    """

    def __init__(
        self,
        show_state: Callable[[SystemState], None],
        restore_active: Callable[[], None],
        *,
        lock_enabled: bool = True,
        idle_enabled: bool = True,
    ) -> None:
        self._show_state = show_state
        self._restore_active = restore_active
        self._lock_enabled = bool(lock_enabled)
        self._idle_enabled = bool(idle_enabled)
        self._coordinator = SystemStateCoordinator()

    @property
    def visible_state(self) -> SystemState:
        return self._coordinator.visible_state

    @property
    def lock_enabled(self) -> bool:
        return self._lock_enabled

    @property
    def idle_enabled(self) -> bool:
        return self._idle_enabled

    def configure(
        self,
        *,
        lock_enabled: bool | None = None,
        idle_enabled: bool | None = None,
    ) -> None:
        """Update policy without disturbing suspend or terminal conditions."""
        previous = self.visible_state

        if lock_enabled is not None:
            enabled = bool(lock_enabled)
            if enabled != self._lock_enabled:
                self._lock_enabled = enabled
                if not enabled:
                    self._coordinator.set_condition(SystemState.LOCKED, False)

        if idle_enabled is not None:
            enabled = bool(idle_enabled)
            if enabled != self._idle_enabled:
                self._idle_enabled = enabled
                if not enabled:
                    self._coordinator.set_condition(SystemState.IDLE, False)

        self._emit_if_changed(previous)

    def handle_condition(self, state: SystemState, enabled: bool) -> None:
        """Apply one condition change and update the visible state if needed."""
        if state is SystemState.ACTIVE:
            return
        if state is SystemState.LOCKED and not self._lock_enabled:
            return
        if state is SystemState.IDLE and not self._idle_enabled:
            return

        previous = self.visible_state
        self._coordinator.set_condition(state, bool(enabled))
        self._emit_if_changed(previous)

    def _emit_if_changed(self, previous: SystemState) -> None:
        current = self.visible_state
        if current is previous:
            return
        if current is SystemState.ACTIVE:
            self._restore_active()
        else:
            self._show_state(current)
