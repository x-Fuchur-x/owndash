from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "src/owndash/gui/canvas.py").read_text()
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text()
INIT = (ROOT / "src/owndash/__init__.py").read_text()



def test_static_layer_cache_exists():
    assert "_static_export_layer" in CANVAS
    assert "_static_scene_signature" in CANVAS
    assert "Completely static dashboards" in CANVAS


def test_motion_cadence_is_adaptive():
    assert "_display_widget_interval_ms" in WINDOW
    assert "_display_idle_interval_ms" in WINDOW


def test_duplicate_usb_frames_are_suppressed():
    assert "payload == self._last_display_payload" in WINDOW


def test_motion_jpeg_quality_is_adaptive():
    assert "quality =" in WINDOW
    assert "self.canvas.has_active_motion()" in WINDOW
