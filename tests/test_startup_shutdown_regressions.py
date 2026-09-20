from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from owndash.core.preferences import AppPreferences
from owndash.core.system_state import SystemState
from owndash.gui.app_window import SafeShutdownWindow
from owndash.service import startup
from owndash.service.autostart import autostart_path, set_autostart_enabled
from owndash.service.system_state_linux import _LogindDbusSource


class FakeVariant:
    def __init__(self, value):
        self._value = value

    def variant(self):
        return self._value


class RecordingStreamer:
    def __init__(self):
        self.running = True
        self.final_frames: list[tuple[bytes, float]] = []

    def submit_final(self, payload: bytes, timeout: float = 1.0) -> bool:
        self.final_frames.append((bytes(payload), float(timeout)))
        return True


@pytest.fixture
def state_window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    prefs = AppPreferences(
        setup_completed=True,
        check_updates=False,
        system_state_screens=True,
        system_state_theme="owndash",
        idle_mode=False,
        lock_screen_state=False,
    )
    monkeypatch.setattr("owndash.gui.main_window.load_preferences", lambda: prefs)
    monkeypatch.setattr("owndash.gui.main_window.SystemSensorProvider.snapshot", lambda self: {})
    monkeypatch.setattr(
        "owndash.service.system_state_linux.LinuxSystemStateAdapter.start",
        lambda self: False,
    )
    monkeypatch.setattr(
        "owndash.service.idle_state.IdleStateMonitor.start",
        lambda self: False,
    )
    window = SafeShutdownWindow()
    yield window
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.hide()
    window.deleteLater()
    app.processEvents()


def test_autostart_entry_requests_minimized_start(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPIMAGE", "/home/markus/Apps/Own Dash.AppImage")

    set_autostart_enabled(True)

    text = autostart_path().read_text(encoding="utf-8")
    assert 'Exec="/home/markus/Apps/Own Dash.AppImage" "--minimized"' in text


def test_startup_cli_consumes_minimized_flag_before_qt_sees_it():
    qt_argv, minimized = startup.resolve_startup_arguments(
        ["OwnDash.AppImage", "--minimized", "--platform", "offscreen"]
    )

    assert minimized is True
    assert qt_argv == ["OwnDash.AppImage", "--platform", "offscreen"]


def test_late_shutdown_metadata_upgrades_pending_transition_to_restart(monkeypatch):
    source = _LogindDbusSource()
    events: list[tuple[str, bool]] = []
    source._callback = lambda kind, enabled: events.append((kind, enabled))
    monkeypatch.setattr(source, "_scheduled_shutdown_kind", lambda: None)

    source._on_prepare_for_shutdown(True)
    source._on_prepare_for_shutdown_with_metadata(
        True,
        {"type": FakeVariant("reboot")},
    )

    assert events == [
        ("terminal_pending", True),
        ("terminal_pending", False),
        ("restart", True),
    ]


def test_desktop_session_commit_pushes_transition_frame_before_logout(state_window):
    window = state_window
    streamer = RecordingStreamer()
    window.display_streamer = streamer
    window.display_connected = True
    window.display_timer.start(250)

    window._handle_session_commit(SimpleNamespace())

    assert window._session_shutdown_requested is True
    assert window._system_state_runtime.visible_state is SystemState.TRANSITIONING
    assert not window.display_timer.isActive()
    assert len(streamer.final_frames) == 1
    payload, timeout = streamer.final_frames[0]
    assert payload
    assert timeout <= 0.35
