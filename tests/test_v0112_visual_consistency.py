from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0112():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def test_numeric_controls_use_one_width():
    assert "NUMERIC_FIELD_WIDTH = 138" in WINDOW
    assert "spin.setFixedWidth(self.NUMERIC_FIELD_WIDTH)" in WINDOW

def test_layout_fields_are_fixed_and_aligned():
    assert "form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)" in WINDOW
    assert "form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)" in WINDOW

def test_forms_share_spacing_system():
    assert "def _polish_form" in WINDOW
    assert "form.setHorizontalSpacing(18)" in WINDOW
    assert "form.setVerticalSpacing(10)" in WINDOW

def test_controls_share_height():
    assert "CONTROL_HEIGHT = 34" in WINDOW
    assert "combo.setMinimumHeight(self.CONTROL_HEIGHT)" in WINDOW
    assert "edit.setMinimumHeight(self.CONTROL_HEIGHT)" in WINDOW
    assert "button.setMinimumHeight(self.CONTROL_HEIGHT)" in WINDOW

def test_background_numeric_controls_are_normalized():
    assert "for spin in (self.bg_opacity_spin, self.bg_x_spin, self.bg_y_spin, self.bg_scale_spin):" in WINDOW
    assert "for spin in (self.aurora_speed_spin, self.aurora_intensity_spin):" in WINDOW

def test_polish_keeps_palette_theme_friendly():
    block = WINDOW[WINDOW.index("    def _apply_ui_polish"):WINDOW.index("    def _make_color_button")]
    assert "palette = QPalette(app.palette()) if app is not None else QPalette(self.palette())" in block
    assert "palette.button().color()" in block
    assert "palette.highlight().color()" in block

