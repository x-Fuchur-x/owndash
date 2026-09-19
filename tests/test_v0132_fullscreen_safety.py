from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
SCREEN = (ROOT / "src/owndash/hardware/screen_display.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0132():
    assert '__version__ = "0.14.0 Beta 4"' in INIT

def test_fullscreen_window_has_escape_signal():
    assert "class FullscreenDisplayWindow(QWidget):" in SCREEN
    assert "escape_requested = Signal()" in SCREEN

def test_escape_and_f11_stop_fullscreen():
    assert "Qt.Key_Escape" in SCREEN
    assert "Qt.Key_F11" in SCREEN
    assert "self.escape_requested.emit()" in SCREEN

def test_fullscreen_window_takes_keyboard_focus():
    assert "self.window.activateWindow()" in SCREEN
    assert "self.window.setFocus(Qt.ActiveWindowFocusReason)" in SCREEN

def test_escape_signal_stops_standard_monitor_stream():
    assert "self._screen_presenter.close_requested.connect(self._stop_display_stream)" in WINDOW

def test_standard_monitor_requires_confirmation():
    assert "QMessageBox.question(" in WINDOW
    assert '"Standard-Monitor starten?"' in WINDOW
    assert "QMessageBox.No" in WINDOW

def test_primary_monitor_gets_extra_warning():
    assert "is_primary = selected_screen is not None and selected_screen is primary" in WINDOW
    assert "Achtung: Du hast deinen Hauptmonitor ausgewählt." in WINDOW

def test_stop_disconnects_presenter_before_backend_close():
    start = WINDOW.index("def _stop_display_stream")
    end = WINDOW.index("def _display_status", start)
    block = WINDOW[start:end]
    assert "presenter.close_requested.disconnect(self._stop_display_stream)" in block
    assert block.index("presenter.close_requested.disconnect") < block.index("streamer.stop()")
