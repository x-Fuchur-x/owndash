from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")
ASSETS = ROOT / "src/owndash/assets"

def test_version_0123():
    assert '__version__ = "0.14.0 Beta 3"' in INIT

def test_theme_specific_spin_arrows_exist():
    for name in (
        "spin-up-dark.svg", "spin-down-dark.svg",
        "spin-up-light.svg", "spin-down-light.svg",
    ):
        assert (ASSETS / name).exists()

def test_spin_arrows_are_selected_by_field_brightness():
    assert 'arrow_suffix = "dark" if base.lightness() >= 128 else "light"' in WINDOW

def test_spinbox_arrow_subcontrols_use_explicit_images():
    assert "QSpinBox::up-arrow, QDoubleSpinBox::up-arrow" in WINDOW
    assert 'image: url("{spin_up_arrow}")' in WINDOW
    assert "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow" in WINDOW
    assert 'image: url("{spin_down_arrow}")' in WINDOW

def test_spin_buttons_have_explicit_subcontrol_positions():
    assert "subcontrol-position: top right;" in WINDOW
    assert "subcontrol-position: bottom right;" in WINDOW
