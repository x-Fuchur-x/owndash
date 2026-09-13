from pathlib import Path

WINDOW = (Path(__file__).resolve().parents[1] / "src/owndash/gui/main_window.py").read_text(encoding="utf-8")

def test_performance_state_exists_before_toolbar_build():
    assert WINDOW.index('self._performance_mode = "Balanced"') < WINDOW.index('self._build_toolbar()')

def test_performance_profiles_exist_before_toolbar_build():
    assert WINDOW.index('self._performance_profiles = {') < WINDOW.index('self._build_toolbar()')
