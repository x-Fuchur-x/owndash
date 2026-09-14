from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW = (ROOT / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0131():
    assert '__version__ = "0.14.0 Beta 2"' in INIT

def _settings_apply_block():
    start = WINDOW.index("        before = self._profile_from_canvas().to_json()", WINDOW.index("def _open_display_settings"))
    end = WINDOW.index("\n    def _set_profile_display_geometry", start)
    return WINDOW[start:end]

def test_active_backend_is_stopped_before_canvas_reconfiguration():
    block = _settings_apply_block()
    stop = block.index("self._stop_display_stream()")
    apply_geometry = block.index("self._set_profile_display_geometry(new_rotation)")
    assert stop < apply_geometry

def test_backend_switch_only_restarts_when_target_changed_and_was_running():
    block = _settings_apply_block()
    assert "target_changed = (" in block
    assert "if target_changed and was_running:" in block
    assert "QTimer.singleShot(0, self._start_display_stream)" in block

def test_unchanged_display_settings_do_not_restart_stream():
    block = _settings_apply_block()
    assert "new_backend != old_backend" in block
    assert "new_device != old_device" in block
    assert "new_rotation != old_rotation" in block

def test_running_state_covers_connecting_streamer_too():
    block = _settings_apply_block()
    assert "self.display_streamer is not None and self.display_streamer.running" in block
