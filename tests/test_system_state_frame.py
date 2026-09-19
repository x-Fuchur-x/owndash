from PySide6.QtGui import QIcon, QImage

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import render_system_state_image


STRINGS = {
    "standby": "Standby",
    "entering_standby": "Entering standby",
    "system_locked": "System locked",
    "shutting_down": "Shutting down",
    "restarting": "Restarting",
    "idle": "Idle",
}


def render(width, height, state, theme="owndash", **kwargs):
    return render_system_state_image(
        width,
        height,
        state,
        theme,
        QIcon(),
        STRINGS,
        **kwargs,
    )


def image_digest(image: QImage) -> bytes:
    return bytes(image.constBits())


def test_all_states_render_exact_size_in_portrait_and_landscape():
    states = [
        SystemState.IDLE,
        SystemState.LOCKED,
        SystemState.SUSPENDING,
        SystemState.SHUTTING_DOWN,
        SystemState.RESTARTING,
    ]
    for width, height in ((480, 1920), (1920, 480), (1280, 720)):
        for theme in ("owndash", "bazzite-inspired"):
            for state in states:
                image = render(width, height, state, theme)
                assert not image.isNull()
                assert image.size().width() == width
                assert image.size().height() == height
                assert image.format() == QImage.Format_RGB32


def test_terminal_and_suspend_states_are_visually_distinct():
    images = {
        state: image_digest(render(640, 360, state))
        for state in (
            SystemState.SUSPENDING,
            SystemState.SHUTTING_DOWN,
            SystemState.RESTARTING,
        )
    }
    assert len(set(images.values())) == 3


def test_themes_are_visually_distinct():
    own = render(640, 360, SystemState.LOCKED, "owndash", clock_text="12:34")
    bazzite = render(640, 360, SystemState.LOCKED, "bazzite-inspired", clock_text="12:34")
    assert image_digest(own) != image_digest(bazzite)


def test_unknown_theme_falls_back_to_owndash():
    expected = render(640, 360, SystemState.SUSPENDING, "owndash")
    fallback = render(640, 360, SystemState.SUSPENDING, "unknown-theme")
    assert image_digest(expected) == image_digest(fallback)


def test_locked_and_idle_accept_optional_context():
    locked = render(
        480,
        1920,
        SystemState.LOCKED,
        clock_text="11:42",
        date_text="19 September 2026",
        sensor_text="CPU 44°C",
    )
    idle = render(
        480,
        1920,
        SystemState.IDLE,
        clock_text="11:42",
        sensor_text="CPU 44°C · GPU 47°C",
    )
    assert not locked.isNull()
    assert not idle.isNull()
    assert image_digest(locked) != image_digest(idle)


def test_active_state_is_not_a_state_screen():
    try:
        render(640, 360, SystemState.ACTIVE)
    except ValueError as exc:
        assert "ACTIVE" in str(exc)
    else:
        raise AssertionError("ACTIVE must not render a temporary state screen")


def test_invalid_dimensions_are_rejected():
    for width, height in ((0, 100), (100, 0), (-1, 100)):
        try:
            render(width, height, SystemState.SUSPENDING)
        except ValueError:
            pass
        else:
            raise AssertionError("non-positive dimensions must be rejected")
