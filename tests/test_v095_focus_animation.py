from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src" / "owndash" / "gui" / "main_window.py"
CANVAS = ROOT / "src" / "owndash" / "gui" / "canvas.py"


def test_spinboxes_ignore_wheel_without_focus():
    source = MAIN.read_text(encoding="utf-8")
    assert "class FocusSafeSpinBox(QSpinBox)" in source
    assert "class FocusSafeDoubleSpinBox(QDoubleSpinBox)" in source
    assert source.count("if not self.hasFocus():") >= 2
    assert source.count("event.ignore()") >= 2


def test_inspector_blank_area_can_take_focus():
    source = MAIN.read_text(encoding="utf-8")
    assert "page.setFocusPolicy(Qt.ClickFocus)" in source
    assert "scroll.viewport().setFocusPolicy(Qt.ClickFocus)" in source


def test_extended_animation_choices_and_controls_exist():
    source = MAIN.read_text(encoding="utf-8")
    for key in ("heartbeat", "flicker", "scanner", "shimmer"):
        assert f'"{key}"' in source
    assert '"animation_speed"' in source
    assert '"animation_strength"' in source


def test_animation_renderer_supports_speed_strength_and_moving_effects():
    source = CANVAS.read_text(encoding="utf-8")
    assert 'self.options.get("animation_speed", 100)' in source
    assert 'self.options.get("animation_strength", 70)' in source
    assert 'elif animation == "heartbeat"' in source
    assert 'elif animation == "flicker"' in source
    assert 'animation in {"scanner", "shimmer", "radar"}' in source
