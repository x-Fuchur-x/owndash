from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
W=(ROOT/"src/owndash/gui/main_window.py").read_text()
I=(ROOT/"src/owndash/project_info.py").read_text()
def test_title_fix():
 assert 'self.setWindowTitle("")' in W
 assert 'self.setWindowTitle(f"{APP_NAME} {__version__}")' not in W
def test_repo_fix():
 assert 'GITHUB_OWNER = "x-Fuchur-x"' in I
 assert 'GITHUB_REPOSITORY = "owndash"' in I
 assert 'f"{GITHUB_ISSUES_URL}/new?"' in W
 assert "Markus-Rosinski/owndash" not in W
