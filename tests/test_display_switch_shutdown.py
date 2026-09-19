from threading import Event

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QDialog

from owndash.core.display import DisplayInfo
from owndash.core.preferences import AppPreferences
from owndash.core.streaming import DisplayStreamer
from owndash.gui.app_window import SafeShutdownWindow


class RecordingDisplay:
    def __init__(self):
        self.events = []

    def connect(self):
        return DisplayInfo("USB", 1920, 480)

    def send_jpeg(self, payload):
        self.events.append(("frame", payload))

    def close(self):
        self.events.append(("close", None))


@pytest.fixture
def running_window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("owndash.gui.main_window.load_preferences", lambda: AppPreferences(setup_completed=True, check_updates=False))
    monkeypatch.setattr("owndash.gui.main_window.SystemSensorProvider.snapshot", lambda self: {})
    window = SafeShutdownWindow()
    backend = RecordingDisplay()
    ready = Event()
    streamer = DisplayStreamer(backend, on_connected=lambda info: ready.set())
    streamer.start()
    assert ready.wait(1)
    window.display_streamer = streamer
    window.display_connected = True
    # The test covers the departing device; don't open the next output.
    monkeypatch.setattr(window, "_start_display_stream", lambda: None)
    yield window, backend, streamer
    streamer.stop()
    window.display_streamer = None
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.hide()
    window.deleteLater()
    app.processEvents()


def test_switch_sends_old_size_shutdown_frame_before_usb_close(running_window, monkeypatch):
    window, backend, streamer = running_window
    rendered = []
    render = window._render_shutdown_frame_payload
    def record_render(reason="quit"):
        assert reason == "switch"
        payload = render(reason=reason)
        rendered.append(payload)
        return payload
    monkeypatch.setattr(window, "_render_shutdown_frame_payload", record_render)
    old_size = (window.canvas.canvas_size.width, window.canvas.canvas_size.height)
    def choose(dialog):
        backend_combo = dialog.findChildren(QComboBox)[0]
        backend_combo.setCurrentIndex(backend_combo.findData("screen"))
        return QDialog.Accepted
    monkeypatch.setattr(QDialog, "exec", choose)
    window._open_display_settings()
    assert len(rendered) == 1
    assert backend.events[0] == ("frame", rendered[0])
    from PySide6.QtGui import QImage
    decoded = QImage.fromData(rendered[0])
    assert (decoded.width(), decoded.height()) == old_size
    assert backend.events[1][0] == "close"
    assert window.display_backend_key == "screen"
    assert not streamer.running


@pytest.mark.parametrize("result", [QDialog.Rejected, QDialog.Accepted])
def test_cancel_or_unchanged_selection_keeps_usb_running(running_window, monkeypatch, result):
    window, backend, streamer = running_window
    monkeypatch.setattr(QDialog, "exec", lambda dialog: result)
    window._open_display_settings()
    assert backend.events == []
    assert streamer.running
