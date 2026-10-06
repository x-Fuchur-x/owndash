from hashlib import sha256
from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QIcon

import owndash.gui.system_state_frame as system_state_frame_module
from owndash.core.system_state import SystemState
from owndash.gui.shutdown_frame import render_shutdown_image
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

# Fresh 480x1920 PNG state artwork. Runtime clock/date/version text is
# deliberately absent from these PNG files and is painted only by the renderer.
_APPROVED_ASSETS = {
    "status_hud_locked.png": "5878fb247cb7f0fa7726742966c262ffde2427de32ad00b7285bd8351029e372",
    "status_hud_idle.png": "52f6239e4db623e6681e50b2209c2fa10d88096b15903a052cc977a3693864fb",
    "status_hud_standby.png": "7547d9b939d311be39bacb82d3a0df88092087e01b5a1672ce2567587b504863",
    "status_hud_shutdown.png": "4122dd6b8c2ecf5282b9e85d02bfab2488e5246ac00de39a198f8cca37e0545c",
    "status_hud_restart.png": "a12b5af10ef2c7bd491337ac1b2578b704232d926172d4b5f62572a6f7fad5b0",
    "status_hud_disconnected.png": "6f185823e4ff02c5591a86ad242bf7119483f232760fbf0b14811b19175f5cd0",
}

_STATE_ASSETS = {
    SystemState.LOCKED: "status_hud_locked.png",
    SystemState.IDLE: "status_hud_idle.png",
    SystemState.SUSPENDING: "status_hud_standby.png",
    SystemState.SHUTTING_DOWN: "status_hud_shutdown.png",
    SystemState.RESTARTING: "status_hud_restart.png",
}

# Points intentionally avoid the live clock/date/footer panel and the animated
# arc. They still cover top logo/frame, side rails, state art and bottom floor.
_APPROVED_STABLE_POINTS = [
    (44, 50),
    (436, 50),
    (240, 150),
    (240, 230),
    (34, 420),
    (446, 420),
    (45, 760),
    (435, 760),
    (45, 980),
    (435, 980),
    (45, 1280),
    (435, 1280),
    (140, 1580),
    (240, 1580),
    (340, 1580),
    (120, 1810),
    (360, 1810),
]


def _digest(image):
    return bytes(image.constBits())


def _approved_asset_rgb(filename: str):
    resource = files("owndash").joinpath("assets", filename)
    with as_file(resource) as path:
        with Image.open(path) as source:
            return source.convert("RGB").copy()


def _assert_preserves_stable_artwork(frame, filename: str):
    approved = _approved_asset_rgb(filename)
    assert frame.width() == 480
    assert frame.height() == 1920
    # State symbols remain original. Frames and floors intentionally now use
    # the locked reference geometry, with state-specific accent colours.
    points = [(x, y) for x in range(180, 301, 4) for y in range(390, 511, 4)]
    if filename == "status_hud_locked.png":
        points += _APPROVED_STABLE_POINTS
    for x, y in points:
        red, green, blue = approved.getpixel((x, y))
        actual = frame.pixelColor(x, y)
        assert abs(actual.red() - red) <= 1
        assert abs(actual.green() - green) <= 1
        assert abs(actual.blue() - blue) <= 1


def test_all_six_approved_hud_assets_are_exact_pngs_and_packaged():
    for filename, expected_sha in _APPROVED_ASSETS.items():
        resource = files("owndash").joinpath("assets", filename)
        data = resource.read_bytes()
        assert sha256(data).hexdigest() == expected_sha

        with as_file(resource) as path:
            with Image.open(path) as source:
                assert source.format == "PNG"
                assert source.size == (480, 1920)


def test_old_stretched_state_jpegs_are_not_packaged():
    for filename in _APPROVED_ASSETS:
        old_name = filename.removesuffix(".png") + ".jpg"
        assert not files("owndash").joinpath("assets", old_name).is_file()


def test_each_system_state_preserves_its_original_symbol():
    for state, filename in _STATE_ASSETS.items():
        frame = render_system_state_image(
            480,
            1920,
            state,
            "owndash",
            QIcon(),
            STRINGS,
            clock_text="21:33",
            date_text="28.09.2026",
            animation_phase=0.0,
        )
        _assert_preserves_stable_artwork(frame, filename)


def test_disconnected_preserves_its_original_symbol():
    frame = render_disconnected_status_image(
        480,
        1920,
        QIcon(),
        status="GETRENNT",
        detail="Keine aktive Verbindung zu OwnDash",
        farewell="",
        theme="owndash",
        clock_text="21:33",
        date_text="28.09.2026",
    )
    _assert_preserves_stable_artwork(frame, "status_hud_disconnected.png")


def test_runtime_clock_and_date_are_drawn_dynamically():
    frame_a = render_system_state_image(
        480,
        1920,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        STRINGS,
        clock_text="18:35",
        date_text="27.09.2026",
        animation_phase=0.0,
    )
    frame_b = render_system_state_image(
        480,
        1920,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        STRINGS,
        clock_text="21:33",
        date_text="28.09.2026",
        animation_phase=0.0,
    )
    assert _digest(frame_a) != _digest(frame_b)


def test_runtime_footer_tracks_current_owndash_version(monkeypatch):
    before = render_system_state_image(
        1024,
        600,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        STRINGS,
        clock_text="21:33",
        date_text="28.09.2026",
        animation_phase=0.0,
    )

    monkeypatch.setattr(system_state_frame_module, "__version__", "9.9.0 Community Test")
    after = render_system_state_image(
        1024,
        600,
        SystemState.LOCKED,
        "owndash",
        QIcon(),
        STRINGS,
        clock_text="21:33",
        date_text="28.09.2026",
        animation_phase=0.0,
    )

    assert _digest(before) != _digest(after)


def test_renderer_has_no_baked_demo_clock_date_or_footer_contract():
    source = Path(render_system_state_image.__code__.co_filename).read_text(encoding="utf-8")
    assert "_REFERENCE_CLOCK" not in source
    assert "_REFERENCE_DATE" not in source
    assert "_REFERENCE_FOOTER" not in source


def test_system_state_renderer_uses_original_png_symbols_without_retired_fallback():
    gui_dir = Path(__file__).resolve().parents[1] / "src" / "owndash" / "gui"
    source = (gui_dir / "system_state_frame.py").read_text(encoding="utf-8")

    for filename in _APPROVED_ASSETS:
        assert filename in source
    assert "status_hud_locked.jpg" not in source
    assert "status_hud_idle.jpg" not in source
    assert "status_hud_standby.jpg" not in source
    assert "status_hud_shutdown.jpg" not in source
    assert "status_hud_restart.jpg" not in source
    assert "status_hud_disconnected.jpg" not in source
    assert "_tint_master" not in source
    assert "_master_variant" not in source
    assert "status_master" not in source
    assert not (gui_dir / "status_master.py").exists()
    assert list(gui_dir.glob("_status_master_data_*.py")) == []


def test_disconnected_shutdown_screen_uses_the_same_visual_renderer_family():
    source = Path(render_shutdown_image.__code__.co_filename).read_text(encoding="utf-8")
    assert "render_disconnected_status_image" in source


def test_persistent_ring_animation_changes_locked_and_idle_frames():
    for state in (SystemState.LOCKED, SystemState.IDLE):
        frame_a = render_system_state_image(
            480,
            1920,
            state,
            "owndash",
            QIcon(),
            STRINGS,
            clock_text="17:42",
            date_text="27.09.2026",
            animation_phase=0.0,
        )
        frame_b = render_system_state_image(
            480,
            1920,
            state,
            "owndash",
            QIcon(),
            STRINGS,
            clock_text="17:42",
            date_text="27.09.2026",
            animation_phase=0.5,
        )
        assert _digest(frame_a) != _digest(frame_b)


def test_terminal_frames_remain_static_for_lifecycle_safety():
    for state in (
        SystemState.SUSPENDING,
        SystemState.SHUTTING_DOWN,
        SystemState.RESTARTING,
    ):
        frame_a = render_system_state_image(
            480,
            1920,
            state,
            "owndash",
            QIcon(),
            STRINGS,
            animation_phase=0.0,
        )
        frame_b = render_system_state_image(
            480,
            1920,
            state,
            "owndash",
            QIcon(),
            STRINGS,
            animation_phase=0.7,
        )
        assert _digest(frame_a) == _digest(frame_b)
