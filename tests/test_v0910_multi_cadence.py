from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "src/owndash/gui/canvas.py").read_text()
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text()
INIT = (ROOT / "src/owndash/__init__.py").read_text()

def test_version_is_0910():
    assert '__version__ = "0.14.0 Beta 1"' in INIT

def test_three_performance_modes_exist():
    for mode in ("Eco", "Balanced", "Smooth"):
        assert f'"{mode}"' in WINDOW
    assert 'addMenu("Performance")' in WINDOW

def test_widget_and_aurora_cadence_are_independent():
    assert "_display_widget_interval_ms" in WINDOW
    assert "_display_aurora_interval_ms" in WINDOW
    assert "has_widget_motion()" in WINDOW
    assert "has_aurora_motion()" in WINDOW

def test_aurora_has_its_own_export_cache():
    assert "_aurora_export_image" in CANVAS
    assert "_aurora_export_interval_s" in CANVAS
    assert "aurora_due" in CANVAS

def test_sensor_refresh_stays_one_hz():
    assert "self.live_timer.start(1000)" in WINDOW
