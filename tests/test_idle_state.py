from owndash.service.idle_state import IdleStateMonitor


class FakeIdleSource:
    def __init__(self, *, available=True, idle=False, idle_since=0.0):
        self.available = available
        self.idle = idle
        self.idle_since = idle_since
        self.callback = None
        self.stopped = False

    def start(self, callback):
        self.callback = callback
        return self.available

    def stop(self):
        self.stopped = True

    def snapshot(self):
        return self.idle, self.idle_since

    def emit(self, *, idle, idle_since):
        self.idle = idle
        self.idle_since = idle_since
        assert self.callback is not None
        self.callback()


class ManualClock:
    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value


def test_does_not_enter_idle_before_threshold_then_enters_once():
    clock = ManualClock(100.0)
    source = FakeIdleSource(idle=True, idle_since=90.0)
    monitor = IdleStateMonitor(source=source, timeout_seconds=30, clock=clock, auto_schedule=False)
    events = []
    monitor.idle_changed.connect(events.append)

    assert monitor.start()
    assert events == []

    clock.value = 119.9
    monitor.check()
    assert events == []

    clock.value = 120.0
    monitor.check()
    monitor.check()
    assert events == [True]


def test_active_session_exits_idle_immediately():
    clock = ManualClock(100.0)
    source = FakeIdleSource(idle=True, idle_since=60.0)
    monitor = IdleStateMonitor(source=source, timeout_seconds=30, clock=clock, auto_schedule=False)
    events = []
    monitor.idle_changed.connect(events.append)
    monitor.start()
    assert events == [True]

    source.emit(idle=False, idle_since=0.0)
    assert events == [True, False]


def test_unavailable_source_fails_open():
    source = FakeIdleSource(available=False, idle=True, idle_since=0.0)
    monitor = IdleStateMonitor(source=source, timeout_seconds=60, auto_schedule=False)
    events = []
    monitor.idle_changed.connect(events.append)

    assert monitor.start() is False
    assert monitor.is_available is False
    assert monitor.is_idle is False
    assert events == []


def test_disabled_monitor_never_enters_idle():
    clock = ManualClock(1000.0)
    source = FakeIdleSource(idle=True, idle_since=0.0)
    monitor = IdleStateMonitor(
        source=source,
        timeout_seconds=60,
        clock=clock,
        enabled=False,
        auto_schedule=False,
    )
    events = []
    monitor.idle_changed.connect(events.append)

    assert monitor.start()
    monitor.check()
    assert monitor.is_idle is False
    assert events == []


def test_invalid_timeout_is_clamped_to_safe_minimum():
    monitor = IdleStateMonitor(source=FakeIdleSource(), timeout_seconds=0, auto_schedule=False)
    assert monitor.timeout_seconds == monitor.MIN_IDLE_SECONDS


def test_stop_clears_state_without_spurious_signal():
    clock = ManualClock(100.0)
    source = FakeIdleSource(idle=True, idle_since=0.0)
    monitor = IdleStateMonitor(source=source, timeout_seconds=60, clock=clock, auto_schedule=False)
    events = []
    monitor.idle_changed.connect(events.append)
    monitor.start()
    assert events == [True]

    monitor.stop()
    assert source.stopped
    assert monitor.is_idle is False
    assert events == [True]
