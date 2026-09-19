from owndash.core.preferences import AppPreferences
from owndash.i18n import tr


def test_beta4_preferences_migrate_to_system_state_defaults():
    prefs = AppPreferences.from_raw({
        "language": "de",
        "appearance": "dark",
        "setup_completed": True,
        "check_updates": False,
    })
    assert prefs.system_state_screens is True
    assert prefs.system_state_theme == "owndash"
    assert prefs.idle_mode is True
    assert prefs.idle_timeout_minutes == 30
    assert prefs.lock_screen_state is True


def test_system_state_preferences_accept_valid_values():
    prefs = AppPreferences.from_raw({
        "system_state_screens": False,
        "system_state_theme": "bazzite-inspired",
        "idle_mode": False,
        "idle_timeout_minutes": 90,
        "lock_screen_state": False,
    })
    assert prefs.system_state_screens is False
    assert prefs.system_state_theme == "bazzite-inspired"
    assert prefs.idle_mode is False
    assert prefs.idle_timeout_minutes == 90
    assert prefs.lock_screen_state is False


def test_invalid_theme_and_timeout_fall_back_or_clamp():
    invalid = AppPreferences.from_raw({
        "system_state_theme": "not-a-theme",
        "idle_timeout_minutes": "nope",
    })
    assert invalid.system_state_theme == "owndash"
    assert invalid.idle_timeout_minutes == 30

    too_small = AppPreferences.from_raw({"idle_timeout_minutes": 0})
    too_large = AppPreferences.from_raw({"idle_timeout_minutes": 99999})
    assert too_small.idle_timeout_minutes == 1
    assert too_large.idle_timeout_minutes == 240


def test_system_state_i18n_strings_are_available_in_english():
    expected = {
        "Standby": "Standby",
        "Standby wird vorbereitet": "Entering standby",
        "System gesperrt": "System locked",
        "Herunterfahren": "Shutting down",
        "Neustart": "Restarting",
        "Systemzustandsanzeigen": "System state screens",
        "Bazzite-inspiriert": "Bazzite-inspired",
        "Ruhemodus": "Idle mode",
        "Zeit bis Ruhemodus": "Idle timeout",
        "Sperrbildschirm berücksichtigen": "Lock screen handling",
    }
    for source, english in expected.items():
        assert tr(source, "en") == english
        assert tr(source, "de") == source
