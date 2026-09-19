from owndash.core.system_state import SystemState
from owndash.service.system_state_linux import LinuxSystemStateAdapter


class FakeSource:
    def __init__(self, available=True):
        self.available = available
        self.callback = None
        self.stopped = False

    def start(self, callback):
        self.callback = callback
        return self.available

    def stop(self):
        self.stopped = True

    def emit(self, kind, enabled=True):
        assert self.callback is not None
        self.callback(kind, enabled)


def test_translates_sleep_and_lock_events():
    source = FakeSource()
    adapter = LinuxSystemStateAdapter(source=source)
    events = []
    adapter.condition_changed.connect(lambda state, enabled: events.append((state, enabled)))
    assert adapter.start()

    source.emit("sleep", True)
    source.emit("sleep", False)
    source.emit("lock", True)
    source.emit("lock", False)

    assert events == [
        (SystemState.SUSPENDING, True),
        (SystemState.SUSPENDING, False),
        (SystemState.LOCKED, True),
        (SystemState.LOCKED, False),
    ]


def test_positive_restart_evidence_is_distinct_from_shutdown():
    source = FakeSource()
    adapter = LinuxSystemStateAdapter(source=source)
    events = []
    adapter.condition_changed.connect(lambda state, enabled: events.append((state, enabled)))
    adapter.start()

    source.emit("restart", True)
    assert events[-1] == (SystemState.RESTARTING, True)

    source.emit("restart", False)
    source.emit("shutdown", True)
    assert events[-1] == (SystemState.SHUTTING_DOWN, True)


def test_duplicate_source_event_is_suppressed():
    source = FakeSource()
    adapter = LinuxSystemStateAdapter(source=source)
    events = []
    adapter.condition_changed.connect(lambda state, enabled: events.append((state, enabled)))
    adapter.start()

    source.emit("sleep", True)
    source.emit("sleep", True)
    assert events == [(SystemState.SUSPENDING, True)]


def test_terminal_states_are_mutually_exclusive():
    source = FakeSource()
    adapter = LinuxSystemStateAdapter(source=source)
    events = []
    adapter.condition_changed.connect(lambda state, enabled: events.append((state, enabled)))
    adapter.start()

    source.emit("shutdown", True)
    source.emit("restart", True)
    assert events[-2:] == [
        (SystemState.SHUTTING_DOWN, False),
        (SystemState.RESTARTING, True),
    ]


def test_unavailable_source_fails_open_without_exception():
    source = FakeSource(available=False)
    adapter = LinuxSystemStateAdapter(source=source)
    availability = []
    adapter.availability_changed.connect(availability.append)

    assert adapter.start() is False
    assert adapter.is_available is False
    assert availability == []

    adapter.stop()
    assert source.stopped
