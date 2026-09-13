from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_canvas_contains_interactive_background_editor_hooks():
    text = (project_root() / "src" / "owndash" / "gui" / "canvas.py").read_text(encoding="utf-8")
    assert "class BackgroundImageItem" in text
    assert "background_image_dropped" in text
    assert "fit_background_image" in text
    assert "center_background_image" in text


def test_main_window_exposes_background_edit_controls():
    text = (project_root() / "src" / "owndash" / "gui" / "main_window.py").read_text(encoding="utf-8")
    assert "Bild direkt auf dem Display bearbeiten" in text
    assert "Hintergrundbild aktiv" in text
    assert "Einpassen" in text
