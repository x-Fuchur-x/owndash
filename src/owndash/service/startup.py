from __future__ import annotations

from collections.abc import Sequence


def resolve_startup_arguments(argv: Sequence[str]) -> tuple[list[str], bool]:
    """Separate OwnDash-only launch flags from arguments passed to Qt."""
    args = list(argv)
    if not args:
        return [], False
    minimized = "--minimized" in args[1:]
    qt_argv = [args[0], *(arg for arg in args[1:] if arg != "--minimized")]
    return qt_argv, minimized


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
