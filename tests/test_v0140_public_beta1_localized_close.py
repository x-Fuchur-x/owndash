from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = (ROOT / "src/owndash/__init__.py").read_text()
PROJECT = (ROOT / "pyproject.toml").read_text()
I18N = (ROOT / "src/owndash/i18n.py").read_text()
MAIN = (ROOT / "src/owndash/gui/main_window.py").read_text()

def test_public_beta1_version():
    assert '__version__ = "0.14.0 Beta 4"' in INIT
    assert 'version = "0.14.0b4"' in PROJECT

def test_close_buttons_follow_owndash_language():
    assert '"Schließen": "Close"' in I18N
    assert MAIN.count('close_button.setText(self._t("Schließen"))') == 5
