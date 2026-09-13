from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src" / "owndash" / "gui" / "main_window.py"
CANVAS = ROOT / "src" / "owndash" / "gui" / "canvas.py"
MODELS = ROOT / "src" / "owndash" / "core" / "models.py"


def test_animation_phase_is_time_based_and_precise():
    source = CANVAS.read_text(encoding="utf-8")
    assert "time.monotonic()" in source
    assert "setTimerType(Qt.PreciseTimer)" in source
    assert "self._animation_timer.start(50)" in source


def test_display_uses_adaptive_motion_cadence():
    source = MAIN.read_text(encoding="utf-8")
    assert "self._display_widget_interval_ms" in source
    assert "self._display_idle_interval_ms" in source
    assert "def _update_display_cadence" in source
    assert "self.canvas.has_widget_motion()" in source


def test_streaming_still_drops_stale_frames():
    source = (ROOT / "src" / "owndash" / "core" / "streaming.py").read_text(encoding="utf-8")
    assert "Queue(maxsize=1)" in source
    assert "get_nowait" in source


def test_dynamic_background_mode_is_profile_compatible():
    source = MODELS.read_text(encoding="utf-8")
    canvas = CANVAS.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    assert "solid | gradient | image | aurora" in source
    assert 'config.mode == "aurora"' in canvas
    assert '"aurora"' in main
