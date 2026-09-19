from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
CANVAS = (ROOT / "src/owndash/gui/canvas.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0100():
    assert '__version__ = "0.14.0 Beta 4"' in INIT

def test_animation_tab_keeps_inspector_clean():
    assert 'addTab(animation_page, "Animation")' in WINDOW
    assert 'QGroupBox("Motion & Regeln")' in WINDOW

def test_trigger_modes_are_exposed():
    for key in ("always", "warning", "critical", "above", "below"):
        assert f'"{key}"' in WINDOW

def test_conditional_animation_drives_render_cadence():
    assert "def animation_is_active" in CANVAS
    assert "animated = [item for item in widgets if item.animation_is_active()]" in CANVAS
    assert "return any(item.animation_is_active()" in CANVAS

def test_new_motion_effects_exist():
    assert '"Color Flow", "colorflow"' in WINDOW
    assert '"Radar Sweep", "radar"' in WINDOW
    assert 'animation == "colorflow"' in CANVAS
    assert 'animation == "radar"' in CANVAS

def test_smooth_alert_colors_exist():
    assert "def _alert_mix" in CANVAS
    assert '"alert_colors"' in WINDOW
