from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "src/owndash/__main__.py").read_text(encoding="utf-8")
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")

def test_kde_caption_uses_full_application_display_name():
    assert 'app.setApplicationDisplayName(f"{APP_NAME} {__version__}")' in MAIN
    assert 'self.setWindowTitle("")' in WINDOW
    assert "self.setWindowTitle(__version__)" not in WINDOW

def test_bug_report_template_is_english():
    assert "## Description" in WINDOW
    assert "## Steps to reproduce" in WINDOW
    assert "## Expected behavior" in WINDOW
    assert "## System information" in WINDOW
    assert "## Additional context" in WINDOW
    assert "## Beschreibung" in WINDOW
    assert "## Schritte zum Reproduzieren" in WINDOW

def test_bug_report_does_not_encode_literal_backslash_n_sequences():
    start = WINDOW.index("def _report_bug")
    end = WINDOW.index("def _available_screen_devices", start)
    block = WINDOW[start:end]
    assert "\\\\n" not in block

def test_about_has_correct_mit_compatible_copyright_notice():
    assert "Markus Rosinski © 2026" in WINDOW
    assert "All rights reserved" not in WINDOW
