from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")
I18N = (ROOT / "src/owndash/i18n.py").read_text(encoding="utf-8")

def test_beta3_version():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def test_about_layout_and_credit():
    assert "dialog.setMinimumSize(560, 480)" in WINDOW
    assert "note.setMinimumHeight(64)" in WINDOW
    assert "Entwickler / Copyright" in WINDOW
    assert "Markus Rosinski © 2026" in WINDOW
    assert "Copyright © 2026 Markus Rosinski" not in WINDOW

def test_credit_label_localized():
    assert '"Entwickler / Copyright": "Developer / Copyright"' in I18N

def test_bug_report_follows_language():
    assert 'if self.language == "de":' in WINDOW
    for text in ("## Beschreibung", "## Schritte zum Reproduzieren", "## Description", "## Steps to reproduce"):
        assert text in WINDOW

def test_bug_report_has_real_newlines():
    start = WINDOW.index("def _report_bug")
    end = WINDOW.index("def _available_screen_devices", start)
    block = WINDOW[start:end]
    assert "\\\\n" not in block
