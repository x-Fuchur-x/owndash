from __future__ import annotations

import os
from pathlib import Path

from .models import Profile


def default_config_dir() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg_config_home).expanduser() if xdg_config_home else Path.home() / ".config"
    return base / "owndash"


def default_profile_path() -> Path:
    return default_config_dir() / "profiles" / "default.json"


def startup_snapshot_path() -> Path:
    return default_config_dir() / "profiles" / "last-session.json"


def save_profile(profile: Profile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(profile.to_json(), encoding="utf-8")
    tmp.replace(path)


def load_profile(path: Path) -> Profile:
    return Profile.from_json(path.read_text(encoding="utf-8"))
