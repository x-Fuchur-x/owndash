from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0117():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def test_tab_widget_pane_has_connected_frame():
    assert "QTabWidget::pane {{" in WINDOW
    assert "top: -1px;" in WINDOW

def test_tabs_touch_each_other_like_registers():
    assert "margin-right: -1px;" in WINDOW
    assert "border-top-left-radius: 6px;" in WINDOW
    assert "border-top-right-radius: 6px;" in WINDOW

def test_selected_tab_visually_merges_into_pane():
    assert "QTabBar::tab:selected {{" in WINDOW
    assert "border-bottom-color: {window.name()};" in WINDOW
    assert "background-color: {window.name()};" in WINDOW

def test_tabs_keep_hover_feedback():
    assert "QTabBar::tab:hover {{" in WINDOW
    assert "background-color: {light.name()};" in WINDOW

def test_tabbar_draws_native_base():
    assert "tabbar.setDrawBase(True)" in WINDOW
