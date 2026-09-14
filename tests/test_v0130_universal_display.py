from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT/"src/owndash/gui/main_window.py").read_text(encoding="utf-8")
CANVAS = (ROOT/"src/owndash/gui/canvas.py").read_text(encoding="utf-8")
MODELS = (ROOT/"src/owndash/core/models.py").read_text(encoding="utf-8")
SCREEN = (ROOT/"src/owndash/hardware/screen_display.py").read_text(encoding="utf-8")
INIT = (ROOT/"src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def test_profile_persists_display_backend():
    assert 'display_backend: str = "aic_usb"' in MODELS
    assert 'display_device_id: str = "auto"' in MODELS

def test_canvas_can_change_resolution():
    assert "def set_canvas_size" in CANVAS
    assert "sx = width / old_w" in CANVAS
    assert "self._scene.setSceneRect" in CANVAS

def test_standard_monitor_backend_exists():
    assert "class ScreenDisplayBackend" in SCREEN
    assert "class ScreenPresenter" in SCREEN
    assert "frame_ready = Signal(bytes)" in SCREEN

def test_display_selection_ui_exists():
    assert 'QAction("Display auswählen …", self)' in WINDOW
    assert '"aic_usb"' in WINDOW
    assert '"screen"' in WINDOW

def test_monitor_discovery_uses_qt_screens():
    assert "for index, screen in enumerate(app.screens())" in WINDOW

def test_output_backend_is_selected_at_runtime():
    assert 'if profile.display_backend == "screen":' in WINDOW
    assert "AicUsbDisplayBackend(" in WINDOW
    assert "ScreenDisplayBackend(" in WINDOW

def test_detected_resolution_updates_logical_canvas():
    assert "logical_size(width, height, profile.rotation)" in WINDOW
    assert "_resize_dashboard_canvas(logical_w, logical_h, scale_widgets=True)" in WINDOW

def test_standard_monitor_backend_applies_rotation():
    assert "rotation: int = 0" in SCREEN
    assert "image = source.convert(\"RGB\").rotate(-rotation, expand=True)" in SCREEN
