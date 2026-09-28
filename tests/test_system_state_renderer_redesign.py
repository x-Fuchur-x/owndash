from hashlib import sha256
from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QIcon

from owndash.core.system_state import SystemState
from owndash.gui.shutdown_frame import render_shutdown_image
from owndash.gui.system_state_frame import render_disconnected_status_image, render_system_state_image


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

# These are the six 480x1920 designs approved in chat on 2026-09-27.
# Their hashes are the visual contract: production may add only the explicit
# dynamic overlays (localized copy, clock/date and the restrained live sweep).
_APPROVED_ASSETS = {
    "status_hud_locked.jpg": "42f952fec87e0294e36b444153a5b3bd087b68ec5b7357a2d12fbb759ea22335",
    "status_hud_idle.jpg": "367963a02d0de29dced91fe11357bd88da6b13ff147ea9f33150529c0580a94c",
    "status_hud_standby.jpg": "886a0bd2e1df06ff4f7f6ce56f9955eec852a0fea9ef51ab0a06cfc182ba8eb7",
    "status_hud_shutdown.jpg": "2fab18722fef30caf61bac292265f0a12f3af987e603263da20d1a7d487cffb3",
    "status_hud_restart.jpg": "dcced8c771be97610690e6dbd74650515a52de84b1bfb1dc33979c79ad4b7d2a",
    "status_hud_disconnected.jpg": "a830dc609350809295f6acb986292b38f8cabb7f4d68be81349a53ce4037466a",
}

_STATE_ASSETS = {
    SystemState.LOCKED: "status_hud_locked.jpg",
    SystemState.IDLE: "status_hud_idle.jpg",
    SystemState.SUSPENDING: "status_hud_standby.jpg",
    SystemState.SHUTTING_DOWN: "status_hud_shutdown.jpg",
    SystemState.RESTARTING: "status_hud_restart.jpg",
}

# Stable points avoid the areas intentionally repainted for dynamic copy,
# symbol, clock/date and animation. They still hit rails/rings/floor so a
# wrong state artwork or simplified renderer cannot pass unnoticed.
_APPROVED_STABLE_POINTS = [
    (44, 50),
    (436, 50),
    (240, 150),
    (240, 280),
    (82, 455),
    (398, 455),
    (95, 610),
    (385, 610),
    (72, 835),
    (408, 835),
    (45, 900),
    (435, 900),
    (140, 1725),
    (240, 1725),
    (340, 1725),
    (120, 1830),
    (360, 1830),
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
    for x, y in _APPROVED_STABLE_POINTS:
        red, green, blue = approved.getpixel((x, y))
        actual = frame.pixelColor(x, y)
        assert abs(actual.red() - red) <= 1
        assert abs(actual.green() - green) <= 1
        assert abs(actual.blue() - blue) <= 1


def test_all_six_approved_hud_assets_are_exact_and_packaged():
    for filename, expected_sha in _APPROVED_ASSETS.items():
        data = files("owndash").joinpath("assets", filename).read_bytes()
        assert sha256(data).hexdigest() == expected_sha


def test_each_system_state_preserves_its_approved_artwork():
    for state, filename in _STATE_ASSETS.items():
        frame = render_system_state_image(
            480,
            1920,
            state,
            "owndash",
            QIcon(),
            STRINGS,
            clock_text="18:35",
            date_text="27.09.2026",
            animation_phase=0.0,
        )
        _assert_preserves_stable_artwork(frame, filename)


def test_disconnected_preserves_its_approved_artwork():
    frame = render_disconnected_status_image(
        480,
        1920,
        QIcon(),
        status="GETRENNT",
        detail="Keine aktive Verbindung zu OwnDash",
        farewell="",
        theme="owndash",
        clock_text="18:35",
        date_text="27.09.2026",
    )
    _assert_preserves_stable_artwork(frame, "status_hud_disconnected.jpg")


def test_system_state_renderer_uses_exact_state_assets_without_recolor_fallback():
    gui_dir = Path(__file__).resolve().parents[1] / "src" / "owndash" / "gui"
    source = (gui_dir / "system_state_frame.py").read_text(encoding="utf-8")

    for filename in _APPROVED_ASSETS:
        assert filename in source
    assert "status_hud_master.jpg" not in source
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
    for state in (SystemState.SUSPENDING, SystemState.SHUTTING_DOWN, SystemState.RESTARTING):
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
