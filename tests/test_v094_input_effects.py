from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = ROOT / "src" / "owndash" / "gui" / "canvas.py"
MAIN = ROOT / "src" / "owndash" / "gui" / "main_window.py"


def _render_jpeg_source() -> str:
    text = CANVAS.read_text(encoding="utf-8")
    start = text.index("    def render_jpeg")
    end = text.index("    def dragEnterEvent", start)
    return text[start:end]


def test_live_export_does_not_clear_scene_selection():
    source = _render_jpeg_source()
    assert "clearSelection()" not in source
    assert "set_export_mode(True)" in source
    assert "set_export_mode(False)" in source


def test_export_mode_hides_editor_chrome_without_deselecting():
    source = CANVAS.read_text(encoding="utf-8")
    assert "self._export_mode = False" in source
    assert "self.isSelected() and not self._export_mode" in source


def test_effects_have_visible_whole_widget_modulation():
    source = CANVAS.read_text(encoding="utf-8")
    assert 'if animation == "pulse"' in source
    assert 'elif animation == "breathe"' in source
    assert "effect_alpha" in source
    assert "background.setAlphaF((opacity / 100.0) * effect_alpha)" in source
    assert "color.alphaF() * effect_alpha" in source


def test_animation_combo_commits_only_on_user_activation():
    source = MAIN.read_text(encoding="utf-8")
    assert "self.animation_combo.activated.connect(self._apply_widget_style)" in source
    assert "self.animation_combo.currentIndexChanged.connect(self._apply_widget_style)" not in source
