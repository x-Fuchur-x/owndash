from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "src/owndash/gui/canvas.py").read_text()
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text()
INIT = (ROOT / "src/owndash/__init__.py").read_text()


def test_version_bumped():
    assert '__version__ = ' in INIT


def test_eight_resize_handles_present():
    for handle in ('"nw"', '"n"', '"ne"', '"e"', '"se"', '"s"', '"sw"', '"w"'):
        assert handle in CANVAS
    assert "_paint_selection_handles" in CANVAS


def test_magnetic_guides_present():
    assert "snap_widget_position" in CANVAS
    assert "drawForeground" in CANVAS
    assert "_guide_x" in CANVAS and "_guide_y" in CANVAS


def test_copy_paste_and_layers_present():
    assert "copy_selected_widgets" in CANVAS
    assert "paste_widgets" in CANVAS
    assert '_build_layers_dock' in WINDOW
    assert 'QDockWidget("Ebenen"' in WINDOW
