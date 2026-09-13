from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src" / "owndash" / "gui" / "main_window.py"
ENTRY = ROOT / "src" / "owndash" / "__main__.py"
CANVAS = ROOT / "src" / "owndash" / "gui" / "canvas.py"
MODELS = ROOT / "src" / "owndash" / "core" / "models.py"


def test_closing_editor_can_keep_live_display_running_in_tray():
    main = MAIN.read_text(encoding="utf-8")
    entry = ENTRY.read_text(encoding="utf-8")
    assert "setQuitOnLastWindowClosed(False)" in entry
    assert "QSystemTrayIcon" in main
    assert "Beim Schließen im Hintergrund weiterlaufen" in main
    assert "event.ignore()" in main
    assert "self.hide()" in main
    assert "OwnDash vollständig beenden" in main


def test_motion_cadence_is_lighter_than_v096():
    main = MAIN.read_text(encoding="utf-8")
    assert "self._display_widget_interval_ms" in main
    assert "self._display_idle_interval_ms" in main
    assert "quality =" in main and "self.canvas.has_active_motion()" in main


def test_aurora_is_user_customizable_and_profile_persistent():
    models = MODELS.read_text(encoding="utf-8")
    canvas = CANVAS.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    for key in ("aurora_color1", "aurora_color2", "aurora_color3", "aurora_speed", "aurora_intensity"):
        assert key in models
        assert key in canvas
        assert key in main
    assert 'QGroupBox("Live Aurora")' in main
    assert 'self.aurora_group.setVisible(config.mode == "aurora")' in main
