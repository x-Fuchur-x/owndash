from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT/"src/owndash/gui/canvas.py").read_text(encoding="utf-8")

def subset_block() -> str:
    start = CANVAS.index("def _render_scene_subset")
    end = CANVAS.index("def render_jpeg", start)
    return CANVAS[start:end]

def test_export_subset_does_not_toggle_visibility():
    block = subset_block()
    assert "setVisible(" not in block
    assert "prior_visibility" not in block

def test_export_subset_uses_temporary_opacity_and_restores_it():
    block = subset_block()
    assert "prior_opacity" in block
    assert "item.setOpacity(1.0 if item in visible_widgets else 0.0)" in block
    assert "item.setOpacity(opacity)" in block

def test_background_opacity_is_restored():
    block = subset_block()
    assert "bg_opacity" in block
    assert "self._background_item.setOpacity(bg_opacity)" in block
