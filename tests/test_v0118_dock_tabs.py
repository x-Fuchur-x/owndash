from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0118():
    assert '__version__ = "0.14.0 Beta 4"' in INIT

def test_dock_tabbars_are_identified_separately():
    assert 'if not isinstance(tabbar.parent(), QTabWidget):' in WINDOW
    assert 'tabbar.setObjectName("dockTabBar")' in WINDOW

def test_dock_tabs_use_bottom_register_geometry():
    assert "QTabBar#dockTabBar::tab {{" in WINDOW
    assert "border-bottom-left-radius: 6px;" in WINDOW
    assert "border-bottom-right-radius: 6px;" in WINDOW
    assert "border-top-left-radius: 0;" in WINDOW

def test_selected_dock_tab_merges_upward_into_dock():
    assert "QTabBar#dockTabBar::tab:selected {{" in WINDOW
    assert "border-top-color: {window.name()};" in WINDOW

def test_dock_tabs_keep_hover_feedback():
    assert "QTabBar#dockTabBar::tab:hover {{" in WINDOW
