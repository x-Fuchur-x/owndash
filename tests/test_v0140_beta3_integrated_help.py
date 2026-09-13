from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
I18N = (ROOT/"src/owndash/i18n.py").read_text(encoding="utf-8")

def test_help_menu_entry_exists():
    assert 'QAction("OwnDash-Hilfe …", self)' in WINDOW
    assert "help_action.triggered.connect(self._show_help_dialog)" in WINDOW

def test_help_uses_scrollable_text_browser():
    assert "QTextBrowser" in WINDOW
    assert "browser.setOpenExternalLinks(True)" in WINDOW

def test_help_is_bilingual():
    assert 'if self.language == "de":' in WINDOW
    assert "<h3>Erste Schritte</h3>" in WINDOW
    assert "<h3>Getting started</h3>" in WINDOW
    assert "<h3>FAQ</h3>" in WINDOW

def test_help_documents_display_modes_and_safety():
    assert "VSDISPLAY / ArtInChip" in WINDOW
    assert "Standardmonitor" in WINDOW
    assert "Standard monitor" in WINDOW
    assert "Rückgängig-/Sicherheitsfunktion" in WINDOW
    assert "undo/safety mechanism" in WINDOW

def test_help_links_to_project_page():
    assert 'href="{GITHUB_URL}"' in WINDOW

def test_help_labels_localized():
    assert '"OwnDash-Hilfe …": "OwnDash Help …"' in I18N
    assert '"OwnDash-Hilfe": "OwnDash Help"' in I18N
