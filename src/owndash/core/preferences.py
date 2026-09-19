from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .config import default_config_dir


@dataclass(slots=True)
class AppPreferences:
    language: str = "system"       # system | de | en
    appearance: str = "system"     # system | dark | light
    setup_completed: bool = False   # first-run compatibility assistant
    check_updates: bool = True      # background GitHub release check
    system_state_screens: bool = True
    system_state_theme: str = "owndash"  # owndash | bazzite-inspired
    idle_mode: bool = True
    idle_timeout_minutes: int = 30
    lock_screen_state: bool = True

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

        theme = str(raw.get("system_state_theme", "owndash"))
        if theme not in {"owndash", "bazzite-inspired"}:
            theme = "owndash"

        timeout_raw = raw.get("idle_timeout_minutes", 30)
        try:
            idle_timeout_minutes = int(timeout_raw)
        except (TypeError, ValueError, OverflowError):
            idle_timeout_minutes = 30
        # Keep the user-facing range intentionally modest: a one-minute
        # minimum prevents accidental busy transitions, while four hours is
        # still useful for long-running desktop sessions.
        idle_timeout_minutes = max(1, min(240, idle_timeout_minutes))

        return cls(
            language=language,
            appearance=appearance,
            setup_completed=bool(raw.get("setup_completed", False)),
            check_updates=bool(raw.get("check_updates", True)),
            system_state_screens=bool(raw.get("system_state_screens", True)),
            system_state_theme=theme,
            idle_mode=bool(raw.get("idle_mode", True)),
            idle_timeout_minutes=idle_timeout_minutes,
            lock_screen_state=bool(raw.get("lock_screen_state", True)),
        )


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
