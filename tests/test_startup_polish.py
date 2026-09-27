from pathlib import Path

from owndash.core.preferences import AppPreferences


ROOT = Path(__file__).resolve().parents[1]
MAIN_WINDOW = ROOT / "src" / "owndash" / "gui" / "main_window.py"
APP_WINDOW = ROOT / "src" / "owndash" / "gui" / "app_window.py"
CONFIG = ROOT / "src" / "owndash" / "core" / "config.py"


def test_restore_last_profile_preferences_exist_and_default_on():
    prefs = AppPreferences()
    assert getattr(prefs, "restore_last_profile", None) is True
    assert getattr(prefs, "last_profile_path", None) == ""


def test_restore_last_profile_preferences_round_trip_from_raw():
    prefs = AppPreferences.from_raw(
        {
            "restore_last_profile": False,
            "last_profile_path": "/tmp/owndash-demo.json",
        }
    )
    assert getattr(prefs, "restore_last_profile", None) is False
    assert getattr(prefs, "last_profile_path", None) == "/tmp/owndash-demo.json"


def test_main_window_restores_last_profile_and_snapshots_templates():
    source = MAIN_WINDOW.read_text(encoding="utf-8")
    assert "def _preferred_startup_profile_path(self) -> Path:" in source
    assert "def _remember_startup_profile(self, path: Path) -> None:" in source
    assert "def _snapshot_profile_for_startup(self) -> None:" in source
    assert "self._snapshot_profile_for_startup()" in source
    assert "self._remember_startup_profile(self.profile_path)" in source
    assert "startup_snapshot_path()" in source


def test_startup_snapshot_has_dedicated_config_path():
    source = CONFIG.read_text(encoding="utf-8")
    assert "def startup_snapshot_path() -> Path:" in source
    assert '"last-session.json"' in source


def test_startup_settings_keep_wrapped_hint_visible_and_offer_restore_toggle():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "QSizePolicy" in source
    assert "startup_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)" in source
    assert "startup_hint.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)" in source
    assert "Letzte Vorlage / letztes Profil beim Start wiederherstellen" in source
    assert "self.preferences.restore_last_profile = restore_last_check.isChecked()" in source
