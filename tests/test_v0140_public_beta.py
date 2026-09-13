from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT/"src/owndash/__init__.py").read_text(encoding="utf-8")
PYPROJECT = (ROOT/"pyproject.toml").read_text(encoding="utf-8")
CHANGELOG = (ROOT/"CHANGELOG.md").read_text(encoding="utf-8")
CONTRIBUTING = (ROOT/"CONTRIBUTING.md").read_text(encoding="utf-8")

def test_public_beta_version():
    assert '__version__ = "0.14.0 Beta 1"' in INIT
    assert 'version = "0.14.0b1"' in PYPROJECT

def test_clean_window_title():
    assert 'self.setWindowTitle("")' in WINDOW
    assert '— OwnDash' not in WINDOW

def test_help_menu_and_about():
    assert 'addMenu("Hilfe")' in WINDOW
    assert '"Über OwnDash …"' in WINDOW
    assert "Markus Rosinski" in WINDOW
    assert "MIT License" in WINDOW

def test_changelog_ui_and_file():
    assert "def _show_changelog_dialog" in WINDOW
    assert "CHANGELOG.md" in WINDOW
    assert "0.14.0 Beta" in CHANGELOG

def test_bug_report_workflow():
    assert "def _report_bug" in WINDOW
    assert 'f"{GITHUB_ISSUES_URL}/new?"' in WINDOW
    assert "urlencode" in WINDOW
    assert "OwnDash: {version}" in WINDOW

def test_contributing_guidance_exists():
    assert "Bug reports" in CONTRIBUTING
    assert "pytest -q" in CONTRIBUTING

def test_no_ai_attribution_added():
    combined = (WINDOW + CHANGELOG + CONTRIBUTING).lower()
    assert "artificial intelligence" not in combined
    assert "created with ai" not in combined
