from pathlib import Path
import re


def replace_function(path: str, name: str, replacement: str) -> None:
    file = Path(path)
    text = file.read_text()
    pattern = re.compile(rf"def {re.escape(name)}\(.*?(?=\n\ndef |\Z)", re.S)
    text, count = pattern.subn(replacement.rstrip(), text, count=1)
    assert count == 1, f"{path}: {name} replacement count={count}"
    file.write_text(text + ("\n" if not text.endswith("\n") else ""))


replace_function(
    "tests/test_system_state_frame.py",
    "test_portrait_status_layout_uses_compact_identity_hud",
    '''def test_portrait_status_layout_uses_compact_identity_hud():
    layout = _portrait_layout(480, 1920)
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert 480 * 0.84 <= layout.hud_diameter <= 480 * 0.90
    assert 480 * 0.12 <= layout.wordmark_font_px <= 480 * 0.14
    assert 480 * 0.09 <= layout.status_font_px <= 480 * 0.11
    assert 480 * 0.80 <= layout.status_rect.width() <= 480 * 0.88
    assert layout.separator_y > ring_bottom
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.bar_rect.top() > layout.detail_rect.bottom()
''')

replace_function(
    "tests/test_system_state_frame.py",
    "test_portrait_system_state_is_the_hero_element",
    '''def test_portrait_system_state_is_the_hero_element():
    layout = _portrait_layout(480, 1920)
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert 480 * 0.78 <= layout.wordmark_rect.width() <= 480 * 0.82
    assert layout.status_font_px < layout.wordmark_font_px
    assert layout.status_rect.width() > layout.wordmark_rect.width()
    assert layout.status_rect.top() > ring_bottom
''')

replace_function(
    "tests/test_system_state_frame.py",
    "test_portrait_status_composition_is_balanced_for_480x1920",
    '''def test_portrait_status_composition_is_balanced_for_480x1920():
    layout = _portrait_layout(480, 1920)
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert 1920 * 0.22 <= layout.hud_center.y() <= 1920 * 0.25
    assert layout.separator_y > ring_bottom
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()
    assert 1920 * 0.65 <= layout.context_top <= 1920 * 0.70
    assert layout.floor_horizon >= 1920 * 0.86
''')

replace_function(
    "tests/test_system_state_frame.py",
    "test_portrait_branding_has_breathing_room_without_dominating_status",
    '''def test_portrait_branding_has_breathing_room_without_dominating_status():
    layout = _portrait_layout(480, 1920)
    radius = layout.hud_diameter / 2.0

    assert 480 * 0.12 <= layout.wordmark_font_px <= 480 * 0.14
    assert 480 * 0.78 <= layout.wordmark_rect.width() <= 480 * 0.82
    assert layout.brand_icon_rect.width() >= 480 * 0.18
    assert layout.brand_icon_rect.height() == layout.brand_icon_rect.width()
    assert layout.brand_icon_rect.bottom() < layout.wordmark_rect.top()

    icon_center = layout.brand_icon_rect.center()
    assert math.hypot(
        icon_center.x() - layout.hud_center.x(),
        icon_center.y() - layout.hud_center.y(),
    ) + layout.brand_icon_rect.width() / 2.0 < radius * 0.90
''')

replace_function(
    "tests/test_system_state_frame.py",
    "test_portrait_brand_icon_stays_distinct_from_wordmark",
    '''def test_portrait_brand_icon_stays_distinct_from_wordmark():
    layout = _portrait_layout(480, 1920)

    assert layout.brand_icon_rect.width() >= 480 * 0.18
    assert layout.brand_icon_rect.height() == layout.brand_icon_rect.width()
    assert 480 * 0.12 <= layout.wordmark_font_px <= 480 * 0.14
    assert layout.brand_icon_rect.bottom() + 480 * 0.006 <= layout.wordmark_rect.top()
''')

replace_function(
    "tests/test_system_state_frame.py",
    "test_portrait_v3_keeps_status_and_floor_as_separate_visual_zones",
    '''def test_portrait_v3_keeps_status_and_floor_as_separate_visual_zones():
    layout = _portrait_layout(480, 1920)

    assert layout.status_rect.bottom() < layout.detail_rect.top()
    assert layout.detail_rect.bottom() < layout.bar_rect.top()
    assert layout.bar_rect.bottom() < layout.context_top
    assert layout.floor_horizon > layout.context_top
''')

Path("tests/test_system_state_frame_v10.py").write_text('''from PySide6.QtGui import QFontMetricsF, QImage
from PySide6.QtWidgets import QApplication

from owndash.gui.system_state_frame import _fit_single_line_font, _portrait_layout


_APP = QApplication.instance() or QApplication([])


def test_v11_keeps_brand_ring_and_status_as_separate_reference_zones():
    layout = _portrait_layout(480, 1920)
    radius = layout.hud_diameter / 2.0
    hud_top = layout.hud_center.y() - radius
    hud_bottom = layout.hud_center.y() + radius

    assert 1920 * 0.10 <= hud_top <= 1920 * 0.18
    assert hud_bottom < layout.separator_y
    assert layout.brand_icon_rect.top() > hud_top
    assert layout.wordmark_rect.top() > layout.brand_icon_rect.bottom()
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()


def test_v11_long_terminal_headline_fits_reference_safe_width():
    layout = _portrait_layout(480, 1920)
    image = QImage(480, 1920, QImage.Format_RGB32)
    title = "HERUNTERFAHREN"
    safe_rect = layout.status_rect.adjusted(14, 0, -14, 0)
    font = _fit_single_line_font(image, title, safe_rect, layout.status_font_px, bold=False)
    metrics = QFontMetricsF(font)

    assert layout.status_font_px <= 480 * 0.11
    assert safe_rect.left() >= 480 * 0.08
    assert safe_rect.right() <= 480 * 0.92
    assert metrics.horizontalAdvance(title) <= safe_rect.width()


def test_v11_footer_is_separate_below_status_and_context():
    layout = _portrait_layout(480, 1920)

    assert layout.context_top >= 1920 * 0.65
    assert layout.floor_horizon >= 1920 * 0.86
    assert layout.status_rect.bottom() < layout.detail_rect.top()
    assert layout.bar_rect.bottom() < layout.context_top
    assert not hasattr(layout, "status_panel_rect")
''')

Path("tests/test_system_state_frame_v8.py").write_text('''from __future__ import annotations

from owndash.gui.system_state_frame import _portrait_layout


def test_v11_portrait_branding_matches_approved_reference_proportions():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)

    assert width * 0.84 <= layout.hud_diameter <= width * 0.90
    assert layout.brand_icon_rect.width() >= width * 0.18
    assert width * 0.12 <= layout.wordmark_font_px <= width * 0.14
    assert layout.status_font_px < layout.wordmark_font_px


def test_v11_portrait_composition_has_brand_status_context_footer_zones():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert height * 0.22 <= layout.hud_center.y() <= height * 0.25
    assert layout.separator_y > ring_bottom
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()
    assert layout.detail_rect.top() > layout.status_rect.bottom()
    assert layout.bar_rect.top() > layout.detail_rect.bottom()
    assert layout.context_top >= height * 0.65
    assert layout.floor_horizon >= height * 0.86


def test_v11_portrait_layout_keeps_telemetry_tick_band_removed():
    layout = _portrait_layout(480, 1920)
    assert not hasattr(layout, "telemetry_y")
''')

replace_function(
    "tests/test_system_state_frame_v9.py",
    "test_v10_portrait_uses_compact_hero_and_separate_context_zone",
    '''def test_v11_portrait_uses_reference_ring_then_separate_state_block():
    layout = _portrait_layout(480, 1920)
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert layout.separator_y > ring_bottom
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()
    assert layout.context_top >= 1920 * 0.65
    assert layout.bar_rect.bottom() < layout.context_top
''')

replace_function(
    "tests/test_system_state_orientation_polish.py",
    "test_portrait_status_layout_prioritizes_state_over_branding",
    '''def test_portrait_status_layout_matches_approved_reference_hierarchy():
    width, height = 480, 1920
    layout = _portrait_layout(width, height)
    ring_bottom = layout.hud_center.y() + layout.hud_diameter / 2.0

    assert layout.hud_diameter <= width * 0.90
    assert layout.status_font_px < layout.wordmark_font_px
    assert layout.separator_y > ring_bottom
    assert layout.state_icon_rect.top() > layout.separator_y
    assert layout.status_rect.top() > layout.state_icon_rect.bottom()
    assert layout.detail_rect.top() > layout.status_rect.bottom()
    assert layout.bar_rect.top() > layout.detail_rect.bottom()
    assert layout.context_top > layout.bar_rect.bottom()
    assert layout.floor_horizon > layout.context_top
''')
