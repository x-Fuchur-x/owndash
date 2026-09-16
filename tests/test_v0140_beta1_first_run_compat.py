from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
SYSTEM = (ROOT/"src/owndash/sensors/system.py").read_text(encoding="utf-8")
PREFS = (ROOT/"src/owndash/core/preferences.py").read_text(encoding="utf-8")
README = (ROOT/"README.md").read_text(encoding="utf-8")
INIT = (ROOT/"src/owndash/__init__.py").read_text(encoding="utf-8")
PROJECT = (ROOT/"pyproject.toml").read_text(encoding="utf-8")

def test_beta1_version_and_author():
    assert '__version__ = "0.14.0 Beta 3"' in INIT
    assert 'version = "0.14.0b3"' in PROJECT
    assert 'authors = [{ name = "Markus Rosinski" }]' in PROJECT

def test_first_run_is_persistent_and_only_scheduled_when_needed():
    assert "setup_completed: bool = False" in PREFS
    assert 'raw.get("setup_completed", False)' in PREFS
    assert "if not self.preferences.setup_completed:" in WINDOW
    assert "self.preferences.setup_completed = True" in WINDOW
    assert "save_preferences(self.preferences)" in WINDOW

def test_system_check_is_available_from_help():
    assert 'QAction("Systemprüfung …", self)' in WINDOW
    assert "_show_setup_assistant(first_run=False)" in WINDOW

def test_capability_engine_separates_required_and_optional():
    assert "def system_capabilities()" in SYSTEM
    assert '"required": {' in SYSTEM
    assert '"optional": {' in SYSTEM
    assert '"linux": linux' in SYSTEM
    assert '"graphical_session": display_session' in SYSTEM
    assert '"hwmon":' in SYSTEM
    assert '"nvidia_smi": nvidia_tool' in SYSTEM

def test_setup_uses_plain_language_statuses():
    assert '"Bereit"' in WINDOW
    assert '"Optional / nicht verfügbar"' in WINDOW
    assert '"Aufmerksamkeit erforderlich"' in WINDOW
    assert '"OwnDash starten"' in WINDOW

def test_readme_is_beginner_facing():
    assert "Easy first start" in README
    assert "### Required" in README
    assert "### Optional — only for additional features" in README
    assert "self-contained" in README
    assert "Python knowledge is not required" in README
