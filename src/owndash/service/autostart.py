from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Sequence


def autostart_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    config_home = Path(xdg_config_home).expanduser() if xdg_config_home else Path.home() / ".config"
    return config_home / "autostart" / "owndash.desktop"


def _desktop_exec_quote(argument: str) -> str:
    escaped = (
        str(argument)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
    )
    return f'"{escaped}"'


def current_launch_command() -> list[str]:
    appimage = os.environ.get("APPIMAGE", "").strip()
    if appimage:
        return [str(Path(appimage).expanduser())]
    return [sys.executable, "-m", "owndash"]


def render_autostart_entry(command: Sequence[str]) -> str:
    if not command:
        raise ValueError("autostart command must not be empty")
    exec_line = " ".join(_desktop_exec_quote(part) for part in command)
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=OwnDash\n"
        "Comment=Start OwnDash with the desktop session\n"
        f"Exec={exec_line}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def set_autostart_enabled(enabled: bool) -> None:
    path = autostart_path()
    if not enabled:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        render_autostart_entry([*current_launch_command(), "--minimized"]),
        encoding="utf-8",
    )
    tmp.replace(path)
