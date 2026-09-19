from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = (ROOT / "src/owndash/core/models.py").read_text(encoding="utf-8")
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0110():
    assert '__version__ = "0.14.0 Beta 4"' in INIT

def test_dashboard_page_model_exists():
    assert "class DashboardPage" in MODELS
    assert "pages: list[DashboardPage]" in MODELS
    assert "active_page: int = 0" in MODELS
    assert "auto_cycle: bool = False" in MODELS

def test_legacy_profiles_remain_supported():
    assert "if profile.pages:" in WINDOW
    assert "DashboardPage(" in WINDOW
    assert "theme=profile.theme" in WINDOW
    assert "widgets=profile.widgets" in WINDOW

def test_dashboard_manager_ui_exists():
    assert 'QDockWidget("Dashboards"' in WINDOW
    assert '"Neu"' in WINDOW
    assert '"Duplizieren"' in WINDOW
    assert '"Umbenennen"' in WINDOW
    assert '"Löschen"' in WINDOW

def test_auto_cycle_exists():
    assert 'QCheckBox("Automatisch wechseln")' in WINDOW
    assert "self.page_cycle_timer.timeout.connect(self._next_dashboard_page)" in WINDOW
    assert "def _next_dashboard_page" in WINDOW

def test_switch_invalidates_usb_frame_cache():
    assert "self._last_display_payload = None" in WINDOW
