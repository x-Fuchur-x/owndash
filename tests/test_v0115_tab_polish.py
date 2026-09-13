from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0115():
    assert '__version__ = "0.14.0 Beta 1"' in INIT

def test_tabs_have_visible_resting_state():
    assert "QTabBar::tab {{" in WINDOW
    assert "background-color: {button_surface.name()}" in WINDOW
    assert "border: 1px solid {mid.name()}" in WINDOW

def test_selected_tab_is_visually_distinct():
    assert "QTabBar::tab:selected {{" in WINDOW
    assert "border-bottom-color: {window.name()}" in WINDOW
    assert "font-weight: 600" in WINDOW

def test_hover_state_is_distinct():
    assert "QTabBar::tab:hover {{" in WINDOW
    assert "background-color: {light.name()}" in WINDOW

def test_tab_bars_use_compact_non_expanding_layout():
    assert "tabbar.setExpanding(False)" in WINDOW
    assert "tabbar.setUsesScrollButtons(True)" in WINDOW
