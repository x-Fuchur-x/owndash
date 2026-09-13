from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
I18N = (ROOT/"src/owndash/i18n.py").read_text(encoding="utf-8")
INFO = (ROOT/"src/owndash/project_info.py").read_text(encoding="utf-8")

def test_help_menu_has_project_page():
    assert 'QAction("OwnDash auf GitHub", self)' in WINDOW
    assert "github_action.triggered.connect(self._open_project_page)" in WINDOW

def test_about_has_clickable_project_link():
    assert "project_link = QLabel(" in WINDOW
    assert "GITHUB_URL" in WINDOW
    assert "project_link.setOpenExternalLinks(True)" in WINDOW

def test_project_page_uses_central_url():
    assert "GITHUB_ISSUES_URL, GITHUB_URL" in WINDOW
    assert "webbrowser.open(GITHUB_URL)" in WINDOW
    assert 'GITHUB_OWNER = "x-Fuchur-x"' in INFO
    assert 'GITHUB_REPOSITORY = "owndash"' in INFO

def test_project_link_strings_localized():
    assert '"OwnDash auf GitHub": "OwnDash on GitHub"' in I18N
    assert '"Projektseite": "Project page"' in I18N
