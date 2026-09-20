from __future__ import annotations

from owndash.core.system_state import SystemState


def prepare_window_for_session_shutdown(window: object) -> bool:
    """Push a terminal fallback frame before the desktop session closes apps.

    Plasma can begin session teardown before logind's more specific reboot or
    power-off signal reaches OwnDash.  Sending TRANSITIONING here guarantees a
    useful last USB frame; a later logind event can still refine it to restart
    or shutdown while the process remains alive.
    """
    if bool(getattr(window, "_session_shutdown_requested", False)):
        return False

    setattr(window, "_session_shutdown_requested", True)
    preferences = getattr(window, "preferences", None)
    state_screens = bool(
        preferences is not None
        and getattr(preferences, "system_state_screens", False)
    )

    if state_screens:
        handler = getattr(window, "_handle_system_state_condition", None)
        if callable(handler):
            handler(SystemState.TRANSITIONING, True)
            return True

    fallback = getattr(window, "_show_shutdown_frame", None)
    if callable(fallback):
        fallback()
        return True
    return False


def bind_session_shutdown(app: object, window: object) -> bool:
    """Connect Qt session management to the early display-shutdown fallback."""
    signal = getattr(app, "commitDataRequest", None)
    if signal is None or not hasattr(signal, "connect"):
        return False
    signal.connect(lambda _manager: prepare_window_for_session_shutdown(window))
    return True
