from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
APPEARANCE = (ROOT/"src/owndash/appearance.py").read_text(encoding="utf-8")

def test_diagnostics_uses_active_palette():
    assert "window_color = dialog.palette().color(QPalette.Window)" in WINDOW
    assert "dark_ui = window_color.lightness() < 128" in WINDOW

def test_cards_have_distinct_dark_and_light_contrast():
    assert 'card_border = "#596575" if dark_ui else "#aab3c0"' in WINDOW
    assert 'card_background = "#20262e" if dark_ui else "#fbfcfe"' in WINDOW
    assert 'card_title = "#f1f4f8" if dark_ui else "#20252c"' in WINDOW
    assert "border: 1px solid" in WINDOW
    assert "border-radius: 9px" in WINDOW

def test_all_categories_use_same_card_style():
    for name in ("system_box", "cpu_box", "gpu_box", "services_box"):
        assert f"{name}.setStyleSheet(card_style)" in WINDOW

def test_status_and_hint_have_dark_light_variants():
    assert 'status_green = "#43d17a" if dark_ui else "#148a45"' in WINDOW
    assert 'muted_text = "#aeb7c4" if dark_ui else "#5d6673"' in WINDOW
    assert 'hint.setStyleSheet(f"color: {muted_text};")' in WINDOW

def test_application_palette_has_distinct_dark_and_light_paths():
    assert 'dark = mode == "dark"' in APPEARANCE
    assert 'if mode == "system"' in APPEARANCE
    assert 'QColor("#24272d")' in APPEARANCE
    assert 'QColor("#f1f3f5")' in APPEARANCE
