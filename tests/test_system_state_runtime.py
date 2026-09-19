from owndash.core.system_state import SystemState
from owndash.service.system_state_runtime import SystemStateRuntime


def make_runtime(*, lock_enabled=True, idle_enabled=True):
    shown = []
    restored = []
    runtime = SystemStateRuntime(
        shown.append,
        lambda: restored.append(True),
        lock_enabled=lock_enabled,
        idle_enabled=idle_enabled,
    )
    return runtime, shown, restored


def test_idle_then_active_shows_and_restores():
    runtime, shown, restored = make_runtime()
    runtime.handle_condition(SystemState.IDLE, True)
    assert shown == [SystemState.IDLE]
    assert restored == []

    runtime.handle_condition(SystemState.IDLE, False)
    assert shown == [SystemState.IDLE]
    assert restored == [True]


def test_lock_overrides_idle_and_unlock_returns_to_idle_not_active():
    runtime, shown, restored = make_runtime()
    runtime.handle_condition(SystemState.IDLE, True)
    runtime.handle_condition(SystemState.LOCKED, True)
    runtime.handle_condition(SystemState.LOCKED, False)

    assert shown == [SystemState.IDLE, SystemState.LOCKED, SystemState.IDLE]
    assert restored == []


def test_duplicate_and_hidden_lower_priority_events_do_not_render_again():
    runtime, shown, restored = make_runtime()
    runtime.handle_condition(SystemState.LOCKED, True)
    runtime.handle_condition(SystemState.LOCKED, True)
    runtime.handle_condition(SystemState.IDLE, True)

    assert shown == [SystemState.LOCKED]
    assert restored == []


def test_suspend_overrides_lock_then_returns_to_lock():
    runtime, shown, restored = make_runtime()
    runtime.handle_condition(SystemState.LOCKED, True)
    runtime.handle_condition(SystemState.SUSPENDING, True)
    runtime.handle_condition(SystemState.SUSPENDING, False)

    assert shown == [
        SystemState.LOCKED,
        SystemState.SUSPENDING,
        SystemState.LOCKED,
    ]
    assert restored == []


def test_shutdown_and_restart_remain_distinct():
    runtime, shown, _restored = make_runtime()
    runtime.handle_condition(SystemState.SHUTTING_DOWN, True)
    assert shown[-1] is SystemState.SHUTTING_DOWN

    runtime.handle_condition(SystemState.SHUTTING_DOWN, False)
    runtime.handle_condition(SystemState.RESTARTING, True)
    assert shown[-1] is SystemState.RESTARTING


def test_disabled_lock_and_idle_conditions_are_ignored():
    runtime, shown, restored = make_runtime(lock_enabled=False, idle_enabled=False)
    runtime.handle_condition(SystemState.IDLE, True)
    runtime.handle_condition(SystemState.LOCKED, True)

    assert runtime.visible_state is SystemState.ACTIVE
    assert shown == []
    assert restored == []


def test_disabling_current_idle_restores_active():
    runtime, shown, restored = make_runtime()
    runtime.handle_condition(SystemState.IDLE, True)
    runtime.configure(idle_enabled=False)

    assert runtime.visible_state is SystemState.ACTIVE
    assert shown == [SystemState.IDLE]
    assert restored == [True]


def test_disabling_lock_reveals_existing_idle():
    runtime, shown, restored = make_runtime()
    runtime.handle_condition(SystemState.IDLE, True)
    runtime.handle_condition(SystemState.LOCKED, True)
    runtime.configure(lock_enabled=False)

    assert runtime.visible_state is SystemState.IDLE
    assert shown == [SystemState.IDLE, SystemState.LOCKED, SystemState.IDLE]
    assert restored == []


def test_terminal_and_suspend_states_ignore_policy_toggles():
    runtime, shown, restored = make_runtime(lock_enabled=False, idle_enabled=False)
    runtime.handle_condition(SystemState.SUSPENDING, True)
    runtime.configure(lock_enabled=True, idle_enabled=True)

    assert runtime.visible_state is SystemState.SUSPENDING
    assert shown == [SystemState.SUSPENDING]
    assert restored == []
