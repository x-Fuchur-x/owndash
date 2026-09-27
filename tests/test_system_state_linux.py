from PySide6.QtCore import SLOT

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


def test_qdbus_connections_use_qt_slot_wrapper(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_ID", "test-session")
    FakeDBusConnection.bus = FakeBus()
    monkeypatch.setattr(system_state_linux, "QDBusConnection", FakeDBusConnection)
    monkeypatch.setattr(system_state_linux, "QDBusInterface", FakeDBusInterface)

    source = _LogindDbusSource()
    assert source.start(lambda _kind, _enabled: None) is True

    slots = [connection[-1] for connection in FakeDBusConnection.bus.connections]
    assert SLOT("_on_prepare_for_sleep(bool)") in slots
    assert "_on_prepare_for_sleep(bool)" not in slots


def test_start_emits_current_locked_hint_without_polling(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_ID", "test-session")
    FakeDBusConnection.bus = FakeBus()
    monkeypatch.setattr(system_state_linux, "QDBusConnection", FakeDBusConnection)
    monkeypatch.setattr(system_state_linux, "QDBusInterface", FakeDBusInterface)

    source = _LogindDbusSource()
    events = []

    assert source.start(lambda kind, enabled: events.append((kind, enabled))) is True
    assert ("lock", True) in events


def test_locked_hint_property_changes_track_actual_lock_state(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_ID", "test-session")
    FakeDBusConnection.bus = FakeBus()
    monkeypatch.setattr(system_state_linux, "QDBusConnection", FakeDBusConnection)
    monkeypatch.setattr(system_state_linux, "QDBusInterface", FakeDBusInterface)

    source = _LogindDbusSource()
    events = []
    assert source.start(lambda kind, enabled: events.append((kind, enabled))) is True

    assert any(
        interface == "org.freedesktop.DBus.Properties"
        and name == "PropertiesChanged"
        for _service, _path, interface, name, _receiver, _slot in FakeDBusConnection.bus.connections
    )

    events.clear()
    source._on_session_properties_changed(
        source._LOGIN_SESSION,
        {"LockedHint": FakeVariant(False)},
        [],
    )
    assert events == [("lock", False)]


def test_locked_hint_properties_slot_has_exact_dbus_signature():
    source = _LogindDbusSource()
    signature = "_on_session_properties_changed(QString,QVariantMap,QStringList)"
    assert source.metaObject().indexOfSlot(signature) >= 0


def test_ambiguous_shutdown_stays_neutral_until_late_reboot_evidence(monkeypatch):
    source = _LogindDbusSource()
    events = []
    source._callback = lambda kind, enabled: events.append((kind, enabled))
    monkeypatch.setattr(source, "_scheduled_shutdown_kind", lambda: None)

    source._on_prepare_for_shutdown(True)
    assert events == [("terminal_pending", True)]

    source._on_job_new(1, object(), "reboot.target")
    assert events == [
        ("terminal_pending", True),
        ("terminal_pending", False),
        ("restart", True),
    ]


def test_transitioning_state_exists_for_ambiguous_terminal_phase():
    assert "transitioning" in {state.value for state in SystemState}


def test_shutdown_metadata_slot_has_exact_dbus_signature():
    source = _LogindDbusSource()
    signature = "_on_prepare_for_shutdown_with_metadata(bool,QVariantMap)"
    assert source.metaObject().indexOfSlot(signature) >= 0


def test_shutdown_metadata_reboot_avoids_generic_transition():
    source = _LogindDbusSource()
    assert hasattr(source, "_on_prepare_for_shutdown_with_metadata")
    events = []
    source._callback = lambda kind, enabled: events.append((kind, enabled))
    source._on_prepare_for_shutdown_with_metadata(True, {"type": FakeVariant("reboot")})
    source._on_prepare_for_shutdown(True)
    assert events == [("restart", True)]


def test_shutdown_metadata_poweroff_maps_to_shutdown():
    source = _LogindDbusSource()
    assert hasattr(source, "_on_prepare_for_shutdown_with_metadata")
    events = []
    source._callback = lambda kind, enabled: events.append((kind, enabled))
    source._on_prepare_for_shutdown_with_metadata(True, {"type": FakeVariant("power-off")})
    source._on_prepare_for_shutdown(True)
    assert events == [("shutdown", True)]
