from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")

def test_tabified_docks_do_not_draw_native_base_line():
    assert 'tabbar.setObjectName("dockTabBar")' in WINDOW
    assert "tabbar.setDrawBase(False)" in WINDOW

def test_selected_dock_tab_uses_same_frame_color_as_dock():
    block = WINDOW.split("QTabBar#dockTabBar::tab:selected", 1)[1].split("}}", 1)[0]
    assert "border-color: {mid.name()};" in block
    assert "border-color: {button_border.name()};" not in block

def test_first_selected_dock_tab_has_no_light_corner_seam():
    assert "QTabBar#dockTabBar::tab:first:selected" in WINDOW
    assert "border-left-color: {mid.name()};" in WINDOW
    assert "border-bottom-left-radius: 0;" in WINDOW

def test_first_tab_is_not_shifted_outside_dock():
    assert "QTabBar#dockTabBar::tab:first" in WINDOW
    assert "margin-left: 0;" in WINDOW
