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

# These are the six canonical 480x1920 state artworks approved for OwnDash.
# Their hashes are the visual contract: production may add only the explicit
# dynamic overlays (clock/date, runtime footer and the restrained live sweep).
_APPROVED_ASSETS = {
    "status_hud_locked.jpg": "320bd7eb1b775df989152afa6fcdd05e54f6ebf5b83ba75e02c8843453144ad6",
    "status_hud_idle.jpg": "99fe0da1db9d612f4082a826a0a3b8495fa18c7f41a0d95991b666f9c79988f3",
    "status_hud_standby.jpg": "626f846abd0bb0a8070b3571bdee51b7666b5962fb43e70edcaaf02b48a54734",
    "status_hud_shutdown.jpg": "fe4f0c72640be78c5cd39b5eea8e52d80c6d92eb00a3cab33f69f2eeff84245e",
    "status_hud_restart.jpg": "ed1ce9bb2d5acaeaf1c30bc4e8005b4a50b42ccf31c4a351b6a70f89b7d6d389",
    "status_hud_disconnected.jpg": "d08a19c31a8de9f3bf9776d594b144640ba767d4972eb026d37f10a4d583c92b",
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
