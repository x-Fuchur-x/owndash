from owndash.core.system_state import SystemState
from owndash.service import system_state_linux
from owndash.service.system_state_linux import LinuxSystemStateAdapter, _LogindDbusSource


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


class FakeReply:
    class MessageType:
        ErrorMessage = "error"

    def __init__(self, *arguments):
        self._arguments = list(arguments)

    def type(self):
        return "reply"

    def arguments(self):
        return list(self._arguments)


class FakeVariant:
    def __init__(self, value):
        self._value = value

    def variant(self):
        return self._value


class FakeObjectPath:
    def __init__(self, path):
        self._path = path

    def path(self):
        return self._path


class FakeBusInterface:
    def isServiceRegistered(self, _service):
        return True


class FakeBus:
    def __init__(self):
        self.connections = []

    def isConnected(self):
        return True

    def interface(self):
        return FakeBusInterface()

    def connect(self, service, path, interface, name, receiver, slot):
        self.connections.append((service, path, interface, name, receiver, slot))
        return True

    def disconnect(self, *_args):
        return True


class FakeDBusConnection:
    bus = FakeBus()

    @classmethod
    def systemBus(cls):
        return cls.bus


class FakeDBusInterface:
    def __init__(self, _service, path, interface, _bus):
        self.path = path
        self.interface = interface

    def isValid(self):
        return True

    def call(self, method, *args):
        if method == "GetSession":
            return FakeReply(FakeObjectPath("/org/freedesktop/login1/session/test"))
        if method == "Get" and args[-1] == "LockedHint":
            return FakeReply(FakeVariant(True))
        return FakeReply()


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


def test_systemd_jobnew_slot_has_exact_dbus_signature():
    source = _LogindDbusSource()
    signature = "_on_job_new(uint,QDBusObjectPath,QString)"
    assert source.metaObject().indexOfSlot(signature) >= 0


def test_start_emits_current_locked_hint_without_polling(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_ID", "test-session")
    FakeDBusConnection.bus = FakeBus()
    monkeypatch.setattr(system_state_linux, "QDBusConnection", FakeDBusConnection)
    monkeypatch.setattr(system_state_linux, "QDBusInterface", FakeDBusInterface)

    source = _LogindDbusSource()
    events = []

    assert source.start(lambda kind, enabled: events.append((kind, enabled))) is True
    assert ("lock", True) in events
