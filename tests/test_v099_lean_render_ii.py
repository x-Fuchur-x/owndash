from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "src/owndash/gui/canvas.py").read_text()
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text()
INIT = (ROOT / "src/owndash/__init__.py").read_text()


def test_version_is_099_or_newer():
    assert 'APP_NAME = "OwnDash"' in INIT


def test_editor_preview_is_lighter():
    assert "self._animation_timer.start(50)" in CANVAS
    assert "moving and self.isVisible()" in CANVAS


def test_usb_motion_remains_adaptive():
    assert "_update_display_cadence" in WINDOW


def test_motion_jpeg_is_lighter():
    assert "_display_motion_quality" in WINDOW


def test_aurora_uses_low_resolution_export_raster():
    assert "aurora_w = max(96, width // 4)" in CANVAS
    assert "aurora_h = max(384, height // 4)" in CANVAS
    assert "painter.drawImage(QRectF(0, 0, width, height), self._aurora_export_image)" in CANVAS
