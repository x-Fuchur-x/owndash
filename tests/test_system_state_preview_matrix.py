from __future__ import annotations

from tools.render_system_state_previews import PREVIEW_SIZES, PREVIEW_STATES


def test_preview_matrix_covers_required_display_shapes_and_states():
    assert PREVIEW_SIZES == (
        (480, 1920),
        (720, 1280),
        (800, 1280),
        (1024, 1024),
        (1024, 600),
        (1280, 800),
        (1920, 1080),
        (2560, 1440),
    )
    assert tuple(PREVIEW_STATES) == (
        "locked",
        "idle",
        "standby",
        "shutdown",
        "restart",
        "disconnected",
    )
    assert len(PREVIEW_SIZES) * len(PREVIEW_STATES) == 48
