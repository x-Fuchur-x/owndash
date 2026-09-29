from __future__ import annotations

from pathlib import Path
import runpy


_TOOL = Path(__file__).resolve().parents[1] / "tools" / "render_system_state_previews.py"
_PREVIEW_MODULE = runpy.run_path(str(_TOOL))
PREVIEW_SIZES = _PREVIEW_MODULE["PREVIEW_SIZES"]
PREVIEW_STATES = _PREVIEW_MODULE["PREVIEW_STATES"]


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
