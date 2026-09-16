from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_WINDOW = ROOT / "src" / "owndash" / "gui" / "app_window.py"


def test_update_setting_is_exposed_and_persisted():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "def _open_settings(self) -> None:" in source
    assert "update_check = QCheckBox" in source
    assert "update_check.setChecked(self.preferences.check_updates)" in source
    assert "self.preferences.check_updates = update_check.isChecked()" in source
    assert "save_preferences(self.preferences)" in source


def test_update_setting_explains_no_automatic_installation():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "nothing is downloaded or installed automatically" in source.lower()
    assert "nichts automatisch heruntergeladen oder installiert" in source.lower()
