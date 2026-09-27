from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QScrollArea

from owndash.core.display import DisplayCapabilities, DisplayInfo
from owndash.core.preferences import AppPreferences


def window_class():
    from owndash.gui.device_center_window import DeviceCenterWindow

    return DeviceCenterWindow


@pytest.fixture
def device_window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    prefs = AppPreferences(
        setup_completed=True,
        check_updates=False,
        system_state_screens=True,
        system_state_theme="owndash",
        idle_mode=False,
        idle_timeout_minutes=30,
        lock_screen_state=True,
        language="de",
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
    window = window_class()()
    yield window
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.hide()
    window.deleteLater()
    app.processEvents()


def test_device_center_action_is_always_enabled_while_disconnected(device_window):
    window = device_window
    assert window.display_connected is False
    assert window.device_center_action.isEnabled()
    assert window.device_center_action.text() == "Display & Gerät …"


def test_device_center_action_retranslates_when_language_changes(device_window):
    window = device_window
    assert window.device_center_action.text() == "Display & Gerät …"

    window.language = "en"
    window._retranslate_ui()
    assert window.device_center_action.text() == "Display & Device …"

    window.language = "de"
    window._retranslate_ui()
    assert window.device_center_action.text() == "Display & Gerät …"


def test_device_center_dialog_uses_scrollable_content(device_window, monkeypatch):
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)

    device_window._open_device_center()

    dialogs = device_window.findChildren(QDialog)
    assert dialogs
    dialog = dialogs[-1]
    scroll = dialog.findChild(QScrollArea, "deviceCenterScrollArea")
    assert scroll is not None
    assert scroll.widgetResizable() is True
    assert scroll.horizontalScrollBarPolicy().name == "ScrollBarAlwaysOff"


def test_device_diagnostics_remember_connection_disconnect_and_error(device_window, monkeypatch):
    window = device_window
    info = DisplayInfo("USB Bar Display", 1920, 480, 30)

    from owndash.gui.app_window import SafeShutdownWindow

    monkeypatch.setattr(
        SafeShutdownWindow,
        "_display_connected",
        lambda self, _info: setattr(self, "display_connected", True),
    )
    monkeypatch.setattr(
        SafeShutdownWindow,
        "_display_error",
        lambda self, _error: setattr(self, "display_connected", False),
    )

    window._display_connected(info)
    connected = window._device_diagnostic_snapshot()
    assert connected.last_known_info == info
    assert connected.last_connected_at is not None

    window._display_error(RuntimeError("USB display disconnected during transfer"))
    disconnected = window._device_diagnostic_snapshot()
    assert disconnected.last_known_info == info
    assert disconnected.last_error_category.value == "disconnected"
    assert "disconnected" in disconnected.last_error_message
    assert window.device_center_action.isEnabled()


def test_snapshot_refresh_does_not_touch_active_stream_or_timer(device_window):
    window = device_window
    forbidden = []

    class ReadOnlyBackend:
        def get_capabilities(self):
            return DisplayCapabilities()

        def connect(self):
            forbidden.append("connect")
            raise AssertionError("diagnostics must not connect")

        def close(self):
            forbidden.append("close")
            raise AssertionError("diagnostics must not close")

        def send_jpeg(self, _payload):
            forbidden.append("send_jpeg")
            raise AssertionError("diagnostics must not send frames")

        def set_brightness(self, _percent):
            forbidden.append("brightness")
            raise AssertionError("diagnostics must not write controls")

        def set_expansion_mode(self, _enabled):
            forbidden.append("expansion")
            raise AssertionError("diagnostics must not write controls")

    window.display_backend_key = "aic_usb"
    window.display_streamer = SimpleNamespace(backend=ReadOnlyBackend())
    window.display_connected = True
    window._connected_display_info = DisplayInfo("USB Bar Display", 1920, 480, 30)
    window.display_timer.start(250)

    first = window._device_diagnostic_snapshot()
    second = window._device_diagnostic_snapshot()

    assert first.backend_key == second.backend_key == "aic_usb"
    assert window.display_timer.isActive()
    assert forbidden == []


def test_main_entry_uses_device_center_window():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (root / "src/owndash/__main__.py").read_text(encoding="utf-8")
    assert "from owndash.gui.device_center_window import DeviceCenterWindow as MainWindow" in source
