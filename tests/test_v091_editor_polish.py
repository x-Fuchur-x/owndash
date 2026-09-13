from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_keyboard_nudge_and_center_alignment_are_exposed():
    canvas = (project_root() / "src" / "owndash" / "gui" / "canvas.py").read_text(encoding="utf-8")
    main = (project_root() / "src" / "owndash" / "gui" / "main_window.py").read_text(encoding="utf-8")
    assert "def keyPressEvent" in canvas
    assert "ShiftModifier" in canvas
    assert "Horizontal zentrieren" in main
    assert "Vertikal zentrieren" in main


def test_background_precision_controls_are_present():
    main = (project_root() / "src" / "owndash" / "gui" / "main_window.py").read_text(encoding="utf-8")
    assert 'bg_form.addRow("Position X"' in main
    assert 'bg_form.addRow("Position Y"' in main
    assert 'bg_form.addRow("Skalierung"' in main
    assert "_apply_background_transform_controls" in main
