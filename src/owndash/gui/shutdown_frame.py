"""Disconnected/closed OwnDash screen using the unified status visual family."""
from PySide6.QtGui import QIcon, QImage

from .system_state_frame import render_disconnected_status_image


def render_shutdown_image(
    width: int,
    height: int,
    rotation: int,
    icon: QIcon,
    *,
    status: str = "Dashboard paused",
    detail: str = "OwnDash closed",
    farewell: str = "See you soon.",
) -> QImage:
    # The backend rotates this frame exactly like ordinary dashboard frames.
    # Keep the public signature stable while delegating all visuals to the one
    # production status renderer family.
    del rotation
    return render_disconnected_status_image(
        width,
        height,
        icon,
        status=status,
        detail=detail,
        farewell=farewell,
    )
