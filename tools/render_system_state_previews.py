from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QGuiApplication, QIcon

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import (
    render_disconnected_status_image,
    render_system_state_image,
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


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    out = Path("preview/system-state")
    out.mkdir(parents=True, exist_ok=True)
    icon = QIcon()
    common = {
        "width": 480,
        "height": 1920,
        "theme": "owndash",
        "icon": icon,
        "strings": STRINGS,
        "clock_text": "18:35",
        "date_text": "27.09.2026",
        "animation_phase": 0.0,
    }
    states = {
        "locked": SystemState.LOCKED,
        "idle": SystemState.IDLE,
        "standby": SystemState.SUSPENDING,
        "shutdown": SystemState.SHUTTING_DOWN,
        "restart": SystemState.RESTARTING,
    }
    for name, state in states.items():
        image = render_system_state_image(state=state, **common)
        if not image.save(str(out / f"{name}.png"), "PNG"):
            raise RuntimeError(f"failed to save preview for {name}")

    disconnected = render_disconnected_status_image(
        480,
        1920,
        icon,
        status="GETRENNT",
        detail="Keine aktive Verbindung zu OwnDash",
        farewell="",
        theme="owndash",
    )
    if not disconnected.save(str(out / "disconnected.png"), "PNG"):
        raise RuntimeError("failed to save disconnected preview")

    # Keep the Qt application alive until all pixmaps/images have been saved.
    _ = app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
