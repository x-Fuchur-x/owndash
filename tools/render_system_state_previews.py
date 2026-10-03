from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QGuiApplication, QIcon

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import (
    render_disconnected_status_image,
    render_system_state_image,
)


PREVIEW_SIZES = (
    (480, 1920),
    (720, 1280),
    (800, 1280),
    (1024, 1024),
    (1024, 600),
    (1280, 800),
    (1920, 1080),
    (2560, 1440),
)

PREVIEW_STATES = (
    "locked",
    "idle",
    "standby",
    "shutdown",
    "restart",
    "disconnected",
)

STRINGS = {
    "standby": "Standby",
    "entering_standby": "Standby wird vorbereitet",
    "system_locked": "System gesperrt",
    "shutting_down": "Herunterfahren",
    "restarting": "Neustart",
    "system_transition": "Systemwechsel",
    "ending_session": "Aktuelle Sitzung wird beendet",
    "idle": "Leerlauf",
}

_STATE_PREVIEWS = {
    "locked": (
        SystemState.LOCKED,
        {"clock_text": "21:33", "date_text": "28.09.2026"},
    ),
    "idle": (
        SystemState.IDLE,
        {"clock_text": "21:33", "date_text": None},
    ),
    "standby": (
        SystemState.SUSPENDING,
        {"clock_text": None, "date_text": None},
    ),
    "shutdown": (
        SystemState.SHUTTING_DOWN,
        {"clock_text": None, "date_text": None},
    ),
    "restart": (
        SystemState.RESTARTING,
        {"clock_text": None, "date_text": None},
    ),
}


def _save(image, path: Path) -> None:
    if not image.save(str(path), "PNG"):
        raise RuntimeError(f"failed to save preview: {path}")


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    out = Path("preview/system-state")
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.png"):
        stale.unlink()

    icon = QIcon()

    for width, height in PREVIEW_SIZES:
        common = {
            "width": width,
            "height": height,
            "theme": "owndash",
            "icon": icon,
            "strings": STRINGS,
            "animation_phase": 0.0,
        }

        for name, (state, runtime) in _STATE_PREVIEWS.items():
            image = render_system_state_image(
                state=state,
                **common,
                **runtime,
            )
            _save(image, out / f"{name}-{width}x{height}.png")

        disconnected = render_disconnected_status_image(
            width,
            height,
            icon,
            status="GETRENNT",
            detail="Keine aktive Verbindung zu OwnDash",
            farewell="",
            theme="owndash",
            clock_text=None,
            date_text=None,
        )
        _save(disconnected, out / f"disconnected-{width}x{height}.png")

    expected = len(PREVIEW_SIZES) * len(PREVIEW_STATES)
    generated = len(tuple(out.glob("*.png")))
    if generated != expected:
        raise RuntimeError(f"expected {expected} previews, generated {generated}")

    _ = app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
