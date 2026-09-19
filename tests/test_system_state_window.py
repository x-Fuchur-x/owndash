from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox

import owndash.gui.app_window as app_window_module
from owndash.core.preferences import AppPreferences
from owndash.core.system_state import SystemState
from owndash.gui.app_window import SafeShutdownWindow


class RecordingStreamer:
    def __init__(self):
        self.running = True
        self.final_frames: list[tuple[bytes, float]] = []
        self.frames: list[bytes] = []
        self.stop_timeouts: list[float] = []

    def submit_final(self, payload: bytes, timeout: float = 1.0) -> bool:
        self.final_frames.append((bytes(payload), float(timeout)))
        return True

    def submit(self, payload: bytes) -> None:
        self.frames.append(bytes(payload))

    def stop(self, timeout: float = 2.5) -> None:
        self.stop_timeouts.append(float(timeout))
        self.running = False


@pytest.fixture
def state_window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    prefs = AppPreferences(
        setup_completed=True,
        check_updates=False,
        system_state_screens=True,
        system_state_theme="owndash",
        idle_mode=True,
        idle_timeout_minutes=30,
        lock_screen_state=True,
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


def test_suspend_state_sends_one_static_frame_and_pauses_periodic_work(state_window):
    window = state_window
    streamer = RecordingStreamer()
    window.display_streamer = streamer
    window.display_connected = True
    window.display_timer.start(250)
    window.live_timer.start(1000)

    window._handle_system_state_condition(SystemState.SUSPENDING, True)

    assert window._system_state_runtime.visible_state is SystemState.SUSPENDING
    assert not window.display_timer.isActive()
    assert not window.live_timer.isActive()
    assert len(streamer.final_frames) == 1
    payload, timeout = streamer.final_frames[0]
    assert timeout <= 0.35
    image = QImage.fromData(payload)
    assert not image.isNull()
    assert (image.width(), image.height()) == (
        window.canvas.canvas_size.width,
        window.canvas.canvas_size.height,
    )


def test_resume_restores_dashboard_timers_and_pushes_fresh_frame(state_window, monkeypatch):
    window = state_window
    streamer = RecordingStreamer()
    window.display_streamer = streamer
    window.display_connected = True
    window.display_timer.start(250)
    window.live_timer.start(1000)
    pushed = []
    monkeypatch.setattr(window, "_push_display_frame", lambda: pushed.append(True))

    window._handle_system_state_condition(SystemState.SUSPENDING, True)
    window._handle_system_state_condition(SystemState.SUSPENDING, False)

    assert window._system_state_runtime.visible_state is SystemState.ACTIVE
    assert window.display_timer.isActive()
    assert window.live_timer.isActive()
    assert pushed == [True]


def test_lock_suspend_resume_returns_to_lock_without_restarting_dashboard(state_window):
    window = state_window
    streamer = RecordingStreamer()
    window.display_streamer = streamer
    window.display_connected = True

    window._handle_system_state_condition(SystemState.LOCKED, True)
    window._handle_system_state_condition(SystemState.SUSPENDING, True)
    window._handle_system_state_condition(SystemState.SUSPENDING, False)

    assert window._system_state_runtime.visible_state is SystemState.LOCKED
    assert len(streamer.final_frames) == 3
    assert not window.display_timer.isActive()
    assert not window.live_timer.isActive()


def test_master_switch_disables_runtime_and_restores_active(state_window):
    window = state_window
    streamer = RecordingStreamer()
    window.display_streamer = streamer
    window.display_connected = True
    window.display_timer.start(250)
    window.live_timer.start(1000)

    window._handle_system_state_condition(SystemState.IDLE, True)
    assert window._system_state_runtime.visible_state is SystemState.IDLE

    window.preferences.system_state_screens = False
    window._apply_system_state_preferences()

    assert window._system_state_runtime.visible_state is SystemState.ACTIVE
    assert window.display_timer.isActive()
    assert window.live_timer.isActive()


def test_runtime_preferences_update_idle_and_lock_policy(state_window):
    window = state_window
    window.preferences.idle_timeout_minutes = 42
    window.preferences.idle_mode = False
    window.preferences.lock_screen_state = False

    window._apply_system_state_preferences()

    assert window._idle_state_monitor.timeout_seconds == 42 * 60
    assert window._idle_state_monitor.enabled is False
    assert window._system_state_runtime.idle_enabled is False
    assert window._system_state_runtime.lock_enabled is False


def test_usb_disconnect_during_suspend_waits_for_device_and_access_before_reconnect(state_window, monkeypatch):
    window = state_window
    streamer = RecordingStreamer()
    window.display_backend_key = "aic_usb"
    window.display_streamer = streamer
    window.display_connected = True
    window.display_timer.start(250)
    window.live_timer.start(1000)

    warnings = []
    reconnects = []
    scheduled = []
    statuses = iter(
        [
            SimpleNamespace(connected=False, accessible=False),
            SimpleNamespace(connected=True, accessible=False),
            SimpleNamespace(connected=True, accessible=True),
        ]
    )
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))
    monkeypatch.setattr(window, "_start_display_stream", lambda: reconnects.append(True))
    monkeypatch.setattr(
        app_window_module,
        "probe_artinchip_usb",
        lambda: next(statuses),
        raising=False,
    )
    monkeypatch.setattr(
        QTimer,
        "singleShot",
        staticmethod(lambda delay, callback: scheduled.append((int(delay), callback))),
    )

    window._handle_system_state_condition(SystemState.SUSPENDING, True)
    window._display_error(RuntimeError("USB disappeared during suspend"))

    assert warnings == []
    assert window.display_streamer is None
    assert window.display_connected is False
    assert streamer.stop_timeouts == [0.2]
    assert window._resume_reconnect_pending is True

    window._handle_system_state_condition(SystemState.SUSPENDING, False)

    assert reconnects == []
    assert window._resume_reconnect_pending is True
    assert scheduled

    first_delay, first_attempt = scheduled.pop(0)
    assert first_delay >= 500
    first_attempt()
    assert reconnects == []
    assert warnings == []

    _second_delay, second_attempt = scheduled.pop(0)
    second_attempt()
    assert reconnects == []
    assert warnings == []

    _third_delay, third_attempt = scheduled.pop(0)
    third_attempt()
    assert reconnects == [True]
    assert warnings == []


def test_usb_resume_recovery_warns_only_once_after_bounded_retries(state_window, monkeypatch):
    window = state_window
    window.language = "en"
    window.display_backend_key = "aic_usb"
    warnings = []
    scheduled = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))
    monkeypatch.setattr(
        app_window_module,
        "probe_artinchip_usb",
        lambda: SimpleNamespace(connected=True, accessible=False),
        raising=False,
    )
    monkeypatch.setattr(
        QTimer,
        "singleShot",
        staticmethod(lambda delay, callback: scheduled.append((int(delay), callback))),
    )

    window._schedule_usb_resume_reconnect()
    safety = 0
    while scheduled and safety < 20:
        _delay, callback = scheduled.pop(0)
        callback()
        safety += 1

    assert safety < 20
    assert len(warnings) == 1
    assert warnings[0][1] == "Display could not be started"
    assert "USB display" in warnings[0][2]
    assert "access permission" in warnings[0][2]
    assert "USB-Display" not in warnings[0][2]
    assert window._resume_reconnect_pending is False
    assert window._resume_recovery_armed is False


def test_usb_resume_reconnect_status_uses_active_language(state_window, monkeypatch):
    window = state_window
    window.language = "en"
    window.display_backend_key = "aic_usb"
    monkeypatch.setattr(QTimer, "singleShot", staticmethod(lambda *_args: None))

    window._schedule_usb_resume_reconnect()

    assert window.statusBar().currentMessage() == "Reconnecting display after standby …"


def test_lock_hud_animation_is_low_rate_and_uses_nonblocking_frames(state_window):
    window = state_window
    streamer = RecordingStreamer()
    window.display_streamer = streamer
    window.display_connected = True

    window._handle_system_state_condition(SystemState.LOCKED, True)

    assert window._system_state_animation_timer.isActive()
    assert window._system_state_animation_timer.interval() >= 500
    initial_final_frames = len(streamer.final_frames)

    window._advance_system_state_animation()

    assert len(streamer.final_frames) == initial_final_frames
    assert len(streamer.frames) == 1

    window._handle_system_state_condition(SystemState.SUSPENDING, True)
    assert not window._system_state_animation_timer.isActive()


def test_system_state_render_error_uses_active_language(state_window, monkeypatch):
    window = state_window
    window.language = "en"
    window.display_streamer = RecordingStreamer()
    window.display_connected = True

    def fail_render(_state, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(window, "_render_system_state_payload", fail_render)
    window._send_system_state_frame(SystemState.LOCKED)

    assert window.statusBar().currentMessage() == "System state screen could not be rendered: boom"
