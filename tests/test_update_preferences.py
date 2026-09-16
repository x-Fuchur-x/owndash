from owndash.core.preferences import AppPreferences


def test_update_checks_default_to_enabled():
    assert AppPreferences().check_updates is True


def test_legacy_preferences_without_update_field_stay_enabled():
    prefs = AppPreferences.from_raw(
        {"language": "de", "appearance": "dark", "setup_completed": True}
    )
    assert prefs.check_updates is True


def test_explicit_update_opt_out_is_preserved():
    prefs = AppPreferences.from_raw({"check_updates": False})
    assert prefs.check_updates is False


def test_truthy_legacy_values_are_normalized_to_bool():
    prefs = AppPreferences.from_raw({"check_updates": 1})
    assert prefs.check_updates is True
