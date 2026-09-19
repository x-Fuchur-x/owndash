import math

from PySide6.QtGui import QIcon, QImage

from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import (
    _portrait_layout,
    _portrait_rail_docks,
    render_system_state_image,
)


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


def _count_pixels(image: QImage, x0: int, y0: int, x1: int, y1: int, predicate) -> int:
    total = 0
    for y in range(max(0, y0), min(image.height(), y1), 3):
        for x in range(max(0, x0), min(image.width(), x1), 3):
            color = image.pixelColor(x, y)
            if predicate(color.red(), color.green(), color.blue()):
                total += 1
    return total


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


def test_lock_and_idle_hud_phase_changes_visual_frame():
    for state in (SystemState.LOCKED, SystemState.IDLE):
        phase_a = render(480, 1920, state, animation_phase=0.0, clock_text="11:42")
        phase_b = render(480, 1920, state, animation_phase=0.5, clock_text="11:42")
        assert image_digest(phase_a) != image_digest(phase_b)


def test_terminal_states_ignore_animation_phase_for_stable_final_frame():
    for state in (SystemState.SUSPENDING, SystemState.SHUTTING_DOWN, SystemState.RESTARTING):
        phase_a = render(480, 1920, state, animation_phase=0.0)
        phase_b = render(480, 1920, state, animation_phase=0.75)
        assert image_digest(phase_a) == image_digest(phase_b)


def test_owndash_portrait_has_reference_style_side_rails_and_floor_reflections():
    image = render(
        480,
        1920,
        SystemState.LOCKED,
        animation_phase=0.25,
        clock_text="11:42",
        date_text="19.09.2026",
    )

    cyan_left = _count_pixels(
        image,
        0,
        100,
        55,
        1420,
        lambda r, g, b: b > 100 and g > 90 and b > r * 1.35,
    )
    magenta_right = _count_pixels(
        image,
        425,
        100,
        480,
        1420,
        lambda r, g, b: r > 105 and b > 80 and r > g * 1.25,
    )
    neon_floor = _count_pixels(
        image,
        45,
        1580,
        435,
        1910,
        lambda r, g, b: max(r, g, b) > 75 and max(r, g, b) - min(r, g, b) > 38,
    )

    assert cyan_left >= 28
    assert magenta_right >= 28
    assert neon_floor >= 45


def test_portrait_v2_gives_hero_ring_and_status_reference_scale():
    layout = _portrait_layout(480, 1920)

    assert layout.hud_diameter >= 480 * 0.90
    assert layout.wordmark_font_px >= 480 * 0.115
    assert layout.status_font_px >= 480 * 0.095
    assert layout.status_rect.width() >= 480 * 0.86
    assert layout.status_rect.top() > layout.hud_center.y()
    assert layout.bar_rect.width() >= 480 * 0.62


def test_portrait_v3_wordmark_is_the_hero_element():
    layout = _portrait_layout(480, 1920)

    assert layout.wordmark_rect.width() >= 480 * 0.92
    assert layout.wordmark_font_px >= 480 * 0.17
    assert layout.wordmark_font_px > layout.status_font_px * 1.55


def test_portrait_v3_rails_dock_on_outer_ring_instead_of_crossing_it():
    layout = _portrait_layout(480, 1920)
    docks = _portrait_rail_docks(layout)
    radius = layout.hud_diameter / 2.0

    assert len(docks) == 4
    for point in docks:
        distance = math.hypot(
            point.x() - layout.hud_center.x(),
            point.y() - layout.hud_center.y(),
        )
        assert abs(distance - radius) <= radius * 0.015

    upper_left, lower_left, upper_right, lower_right = docks
    assert upper_left.y() < layout.hud_center.y() < lower_left.y()
    assert upper_right.y() < layout.hud_center.y() < lower_right.y()
    assert upper_left.x() < layout.hud_center.x() < upper_right.x()
    assert lower_left.x() < layout.hud_center.x() < lower_right.x()


def test_portrait_v3_keeps_status_and_floor_as_separate_visual_zones():
    layout = _portrait_layout(480, 1920)

    assert layout.status_rect.bottom() < layout.bar_rect.top()
    assert layout.bar_rect.bottom() < 1920 * 0.74
    assert layout.floor_horizon >= 1920 * 0.80


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
