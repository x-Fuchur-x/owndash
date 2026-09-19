from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0124():
    assert '__version__ = "0.14.0 Beta 4"' in INIT

def test_menubar_has_explicit_background_and_text():
    assert "QMenuBar {{" in WINDOW
    assert "background-color: {window.name()};" in WINDOW
    assert "color: {palette.windowText().color().name()};" in WINDOW

def test_menubar_items_have_selected_and_pressed_states():
    assert "QMenuBar::item:selected {{" in WINDOW
    assert "QMenuBar::item:pressed {{" in WINDOW

def test_popup_menus_use_current_palette():
    assert "QMenu {{" in WINDOW
    assert "background-color: {base.name()};" in WINDOW
    assert "color: {palette.text().color().name()};" in WINDOW

def test_popup_menu_selection_is_high_contrast():
    assert "QMenu::item:selected {{" in WINDOW
    assert "color: {highlighted_text.name()};" in WINDOW
