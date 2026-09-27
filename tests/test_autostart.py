from pathlib import Path

from owndash.core.preferences import AppPreferences
from owndash.service.autostart import autostart_path, render_autostart_entry, set_autostart_enabled
from owndash.service.startup import should_auto_start_display


def test_autostart_path_uses_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert autostart_path() == tmp_path / "autostart" / "owndash.desktop"


def test_render_autostart_entry_quotes_appimage_path_with_spaces():
    entry = render_autostart_entry(["/home/markus/Apps/Own Dash.AppImage"])
    assert "[Desktop Entry]" in entry
    assert 'Exec="/home/markus/Apps/Own Dash.AppImage"' in entry
    assert "X-GNOME-Autostart-enabled=true" in entry


def test_set_autostart_enabled_writes_and_removes_entry(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPIMAGE", "/home/markus/Apps/Own Dash.AppImage")

    set_autostart_enabled(True)
    path = autostart_path()
    assert path.exists()
    assert 'Exec="/home/markus/Apps/Own Dash.AppImage"' in path.read_text(encoding="utf-8")

    set_autostart_enabled(False)
    assert not path.exists()
    # Removal is deliberately idempotent.
    set_autostart_enabled(False)


def test_existing_preferences_migrate_startup_flags_safely():
    prefs = AppPreferences.from_raw({"language": "de"})
    assert prefs.launch_at_login is False
    assert prefs.start_display_on_launch is False


def test_startup_preferences_accept_persisted_flags():
    prefs = AppPreferences.from_raw(
        {
            "launch_at_login": True,
            "start_display_on_launch": True,
            "setup_completed": True,
        }
    )
    assert prefs.launch_at_login is True
    assert prefs.start_display_on_launch is True


def test_auto_display_start_requires_opt_in_completed_setup_and_usb_backend():
    assert should_auto_start_display(
        enabled=True,
        setup_completed=True,
        backend_key="aic_usb",
        streamer_running=False,
    )
    assert not should_auto_start_display(
        enabled=False,
        setup_completed=True,
        backend_key="aic_usb",
        streamer_running=False,
    )
    assert not should_auto_start_display(
        enabled=True,
        setup_completed=False,
        backend_key="aic_usb",
        streamer_running=False,
    )
    assert not should_auto_start_display(
        enabled=True,
        setup_completed=True,
        backend_key="screen",
        streamer_running=False,
    )
    assert not should_auto_start_display(
        enabled=True,
        setup_completed=True,
        backend_key="aic_usb",
        streamer_running=True,
    )
