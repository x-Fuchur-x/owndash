from __future__ import annotations


def should_auto_start_display(
    *,
    enabled: bool,
    setup_completed: bool,
    backend_key: str,
    streamer_running: bool,
) -> bool:
    """Return whether OwnDash should reconnect a display on launch.

    Automatic startup is deliberately limited to the known headless-safe
    ArtInChip/VSDISPLAY backend. Standard monitors retain their existing
    confirmation dialog so OwnDash never unexpectedly takes over a user's
    primary desktop screen during login.
    """
    return bool(
        enabled
        and setup_completed
        and backend_key == "aic_usb"
        and not streamer_running
    )
