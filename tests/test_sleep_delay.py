import os
from types import SimpleNamespace

import pytest

from owndash.service import system_state_linux as module
from test_system_state_linux import FakeDBusConnection, FakeDBusInterface, FakeReply


class FakeTimer:
    instances = []

    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.cancelled = False
        self.started = False
        self.instances.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


@pytest.fixture
def source(monkeypatch):
    read_fd, write_fd = os.pipe()
    calls = []

    class Interface(FakeDBusInterface):
        def setTimeout(self, timeout):
            assert timeout <= 500

        def call(self, method, *args):
            if method == 'Inhibit':
                calls.append(args)
                return FakeReply(SimpleNamespace(fileDescriptor=lambda: read_fd))
            return super().call(method, *args)

    monkeypatch.setattr(module, 'QDBusConnection', FakeDBusConnection)
    monkeypatch.setattr(module, 'QDBusInterface', Interface)
    monkeypatch.setattr(module, 'Timer', FakeTimer, raising=False)
    FakeTimer.instances.clear()
    obj = module._LogindDbusSource()
    yield obj, calls
    obj.stop()
    os.close(read_fd)
    os.close(write_fd)


def test_delay_is_held_until_sleep_callback_finishes_then_reacquired(source):
    obj, calls = source
    held = []
    def callback(kind, enabled):
        if kind == 'sleep' and enabled:
            held.append(os.fstat(obj._sleep_delay.fd))
    assert obj.start(callback)
    assert calls == [('sleep', 'OwnDash', 'Send standby frame to display', 'delay')]
    fd = obj._sleep_delay.fd
    obj._on_prepare_for_sleep(True)
    assert held
    with pytest.raises(OSError):
        os.fstat(fd)
    assert obj._sleep_delay is None
    obj._on_prepare_for_sleep(False)
    assert len(calls) == 2
    assert obj._sleep_delay is not None


def test_sleep_callback_failure_still_releases_delay(source):
    obj, _ = source
    def callback(kind, enabled):
        if kind == 'sleep' and enabled:
            raise RuntimeError('render failed')
    obj.start(callback)
    with pytest.raises(RuntimeError):
        obj._on_prepare_for_sleep(True)
    assert obj._sleep_delay is None


def test_watchdog_releases_fd_without_qt_event_loop_and_cannot_close_new_lock(source):
    obj, _ = source
    obj.start(lambda *_: None)
    guard = obj._sleep_delay
    guard.arm()
    timer = FakeTimer.instances[-1]
    assert timer.started and timer.interval <= 0.75
    fd = guard.fd
    timer.callback()
    with pytest.raises(OSError):
        os.fstat(fd)
    obj._on_prepare_for_sleep(False)
    new_fd = obj._sleep_delay.fd
    timer.callback()
    os.fstat(new_fd)


def test_stop_releases_delay(source):
    obj, _ = source
    obj.start(lambda *_: None)
    fd = obj._sleep_delay.fd
    obj.stop()
    with pytest.raises(OSError):
        os.fstat(fd)


def test_denied_delay_does_not_disable_events(source, monkeypatch):
    obj, _ = source
    monkeypatch.setattr(module, 'QDBusInterface', FakeDBusInterface)
    events = []
    assert obj.start(lambda *event: events.append(event))
    obj._on_prepare_for_sleep(True)
    assert ('sleep', True) in events
