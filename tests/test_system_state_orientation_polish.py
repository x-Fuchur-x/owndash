from __future__ import annotations

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

import owndash.gui.app_window as app_window_module
from owndash.core.preferences import AppPreferences
from owndash.core.system_state import SystemState
from owndash.gui.app_window import SafeShutdownWindow


@pytest.fixture
def state_window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    prefs = AppPreferences(
        setup_completed=True,
        check_updates=False,
        system_state_screens=True,
        system_state_theme="bazzite-inspired",
        idle_mode=True,
        idle_timeout_minutes=30,
        lock_screen_state=True,
    )
    monkeypatch.setattr("owndash.gui.main_window.load_preferences", lambda: prefs)
    monkeypatch.setattr("owndash.gui.main_window.SystemSensorProvider.snapshot", lambda self: {})
    monkeypatch.setattr("owndash.service.system_state_linux.LinuxSystemStateAdapter.start", lambda self: False)
    monkeypatch.setattr("owndash.service.idle_state.IdleStateMonitor.start", lambda self: False)
    window = SafeShutdownWindow()
    yield window
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.hide()
    window.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_usb_system_state_renderer_uses_dashboard_logical_orientation(state_window, monkeypatch, rotation):
    """Status art enters the backend in dashboard logical orientation."""
    window = state_window
    window.display_backend_key = "aic_usb"
    window._display_rotation = rotation
    logical_w = int(window.canvas.canvas_size.width)
    logical_h = int(window.canvas.canvas_size.height)
    calls: list[tuple[int, int]] = []

    def fake_render(width, height, *_args, **_kwargs):
        calls.append((int(width), int(height)))
        image = QImage(int(width), int(height), QImage.Format_RGB32)
        image.fill(0)
        return image

    monkeypatch.setattr(app_window_module, "render_system_state_image", fake_render)
    payload = window._render_system_state_payload(SystemState.RESTARTING)
    transport = QImage.fromData(payload)

    assert calls == [(logical_w, logical_h)]
    assert (transport.width(), transport.height()) == (logical_w, logical_h)
