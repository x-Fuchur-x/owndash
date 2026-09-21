from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import _portrait_layout, _portrait_state_copy


def test_reference_layout_separates_brand_status_and_footer():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    # Approved reference: the hero ring owns branding only. State information
    # lives in its own block below the ring, followed by time/date and footer.
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0
    assert layout.separator_y > ring_bottom
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()
    assert layout.detail_rect.top() > layout.status_rect.bottom()
    assert layout.bar_rect.top() > layout.detail_rect.bottom()
    assert layout.context_top > layout.bar_rect.bottom()
    assert layout.floor_horizon > layout.context_top


def test_reference_locked_copy_uses_single_clean_headline():
    headline, detail = _portrait_state_copy(
        SystemState.LOCKED,
        "System gesperrt",
        "",
    )
    assert headline == "GESPERRT"
    assert detail == "System ist gesperrt"


def test_reference_long_states_remain_single_line_headlines():
    headline, detail = _portrait_state_copy(
        SystemState.SHUTTING_DOWN,
        "Herunterfahren",
        "",
    )
    assert headline == "HERUNTERFAHREN"
    assert detail == "System wird sicher beendet"
