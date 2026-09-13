from pathlib import Path

from owndash.core.config import default_config_dir


def test_default_config_dir_honors_xdg_config_home(monkeypatch, tmp_path):
    custom = tmp_path / "config-home"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom))
    assert default_config_dir() == custom / "owndash"


def test_default_config_dir_falls_back_to_home_dot_config(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert default_config_dir() == Path(tmp_path) / ".config" / "owndash"
