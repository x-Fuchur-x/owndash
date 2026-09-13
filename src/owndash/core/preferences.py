from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .config import default_config_dir


@dataclass(slots=True)
class AppPreferences:
    language: str = "system"      # system | de | en
    appearance: str = "system"    # system | dark | light
    setup_completed: bool = False   # first-run compatibility assistant

    @classmethod
    def from_raw(cls, raw: object) -> "AppPreferences":
        if not isinstance(raw, dict):
            return cls()
        language = str(raw.get("language", "system"))
        appearance = str(raw.get("appearance", "system"))
        if language not in {"system", "de", "en"}:
            language = "system"
        if appearance not in {"system", "dark", "light"}:
            appearance = "system"
        setup_completed = bool(raw.get("setup_completed", False))
        return cls(language=language, appearance=appearance, setup_completed=setup_completed)


def preferences_path() -> Path:
    return default_config_dir() / "settings.json"


def load_preferences() -> AppPreferences:
    path = preferences_path()
    if not path.exists():
        return AppPreferences()
    try:
        return AppPreferences.from_raw(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return AppPreferences()


def save_preferences(preferences: AppPreferences) -> None:
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(preferences), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
