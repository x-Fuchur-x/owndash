from owndash.core.system_state import SystemState, SystemStateCoordinator, resolve_visible_state


def test_state_priority():
    states = {SystemState.IDLE, SystemState.LOCKED, SystemState.SUSPENDING}
    assert resolve_visible_state(states) is SystemState.SUSPENDING


def test_shutdown_and_restart_outrank_suspend():
    assert resolve_visible_state({SystemState.SUSPENDING, SystemState.SHUTTING_DOWN}) is SystemState.SHUTTING_DOWN
    assert resolve_visible_state({SystemState.SUSPENDING, SystemState.RESTARTING}) is SystemState.RESTARTING


def test_empty_conditions_are_active():
    assert resolve_visible_state(set()) is SystemState.ACTIVE


def test_duplicate_condition_does_not_emit_transition():
    c = SystemStateCoordinator()
    assert c.set_condition(SystemState.LOCKED, True) is SystemState.LOCKED
    assert c.set_condition(SystemState.LOCKED, True) is None


def test_lock_overrides_idle_then_unlock_returns_to_idle():
    c = SystemStateCoordinator()
    c.set_condition(SystemState.IDLE, True)
    c.set_condition(SystemState.LOCKED, True)
    assert c.visible_state is SystemState.LOCKED
    assert c.set_condition(SystemState.LOCKED, False) is SystemState.IDLE


def test_clearing_suspend_returns_active():
    c = SystemStateCoordinator()
    c.set_condition(SystemState.SUSPENDING, True)
    assert c.set_condition(SystemState.SUSPENDING, False) is SystemState.ACTIVE


def test_lower_priority_change_does_not_emit_while_higher_state_visible():
    c = SystemStateCoordinator()
    c.set_condition(SystemState.LOCKED, True)
    assert c.set_condition(SystemState.IDLE, True) is None
    assert c.visible_state is SystemState.LOCKED
