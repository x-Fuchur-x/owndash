from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
APPEARANCE = (ROOT / "src/owndash/appearance.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0121():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def test_editors_have_explicit_foreground_and_background():
    assert "QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{" in WINDOW
    assert "background-color: {base.name()};" in WINDOW
    assert "color: {palette.text().color().name()};" in WINDOW

def test_disabled_editors_have_separate_surface():
    assert "disabled_field = QColor(base)" in WINDOW
    assert "QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled" in WINDOW

def test_combo_popup_uses_same_palette():
    assert "QComboBox QAbstractItemView {{" in WINDOW
    assert "selection-background-color: {highlight.name()};" in WINDOW

def test_spin_buttons_are_explicitly_styled():
    assert "QSpinBox::up-button, QDoubleSpinBox::up-button" in WINDOW
    assert "QSpinBox::down-button, QDoubleSpinBox::down-button" in WINDOW

def test_light_disabled_palette_has_light_base():
    assert 'QColor("#e5e9ed") if not dark' in APPEARANCE
