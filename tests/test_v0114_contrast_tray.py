from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0114():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def test_resting_button_surface_is_raised_from_dark_palette():
    assert "button_surface = QColor(button)" in WINDOW
    assert "button_surface = button_surface.lighter(132)" in WINDOW
    assert "border: 1px solid {button_border.name()}" in WINDOW

def test_dashboard_buttons_have_stronger_resting_state():
    assert "QPushButton#dashboardActionButton {{" in WINDOW
    assert "font-weight: 600" in WINDOW
    assert "background-color: {button_surface.name()}" in WINDOW

def test_close_to_tray_no_longer_requires_active_display():
    start = WINDOW.index("    def closeEvent(self, event)")
    end = WINDOW.index("\n    def _load_template", start)
    block = WINDOW[start:end]
    assert "and QSystemTrayIcon.isSystemTrayAvailable()" in block
    assert "and (self.display_connected or streamer_running)" not in block
    assert "self.hide()" in block

def test_tray_message_handles_display_stopped_case():
    assert '"OwnDash bleibt im Hintergrund geöffnet."' in WINDOW
