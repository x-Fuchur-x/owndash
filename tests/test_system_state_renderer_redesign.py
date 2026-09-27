from hashlib import sha256
from importlib.resources import as_file, files
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QIcon

from owndash.core.system_state import SystemState
from owndash.gui.shutdown_frame import render_shutdown_image
from owndash.gui.system_state_frame import render_system_state_image


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

_APPROVED_MASTER_SHA256 = "42f952fec87e0294e36b444153a5b3bd087b68ec5b7357a2d12fbb759ea22335"

# Stable points outside all dynamic symbol/copy/clock patches. The exact asset
# SHA protects artwork identity; these points protect the renderer from moving,
# replacing or repainting the approved perimeter/logo/floor geometry.
_APPROVED_STABLE_POINTS = [
    (44, 50),
    (436, 50),
    (240, 150),
    (240, 280),
    (70, 460),
    (410, 460),
    (80, 780),
    (400, 780),
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


def _approved_master_rgb():
    resource = files("owndash").joinpath("assets", "status_hud_master.jpg")
    with as_file(resource) as path:
        with Image.open(path) as source:
            return source.convert("RGB").copy()


def test_approved_hud_master_asset_is_exact_and_packaged():
    data = files("owndash").joinpath("assets", "status_hud_master.jpg").read_bytes()
    assert sha256(data).hexdigest() == _APPROVED_MASTER_SHA256


def test_locked_portrait_preserves_approved_master_landmarks():
    approved = _approved_master_rgb()
    frame = render_system_state_image(
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
    assert frame.width() == 480
    assert frame.height() == 1920

    for x, y in _APPROVED_STABLE_POINTS:
        red, green, blue = approved.getpixel((x, y))
        actual = frame.pixelColor(x, y)
        assert abs(actual.red() - red) <= 1
        assert abs(actual.green() - green) <= 1
        assert abs(actual.blue() - blue) <= 1


def test_system_state_renderer_has_one_master_path_and_no_legacy_artwork():
    gui_dir = Path(__file__).resolve().parents[1] / "src" / "owndash" / "gui"
    source = (gui_dir / "system_state_frame.py").read_text(encoding="utf-8")

    assert "status_hud_master.jpg" in source
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
