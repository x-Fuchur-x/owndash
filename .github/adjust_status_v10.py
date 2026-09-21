from pathlib import Path

# Refine the generated v10 composition after the main structural patch.
frame = Path("src/owndash/gui/system_state_frame.py")
text = frame.read_text()
text = text.replace(
    'wordmark_rect=QRectF(width * 0.10, height * 0.218, width * 0.80, height * 0.055),',
    'wordmark_rect=QRectF(width * 0.10, height * 0.220, width * 0.80, height * 0.045),',
    1,
)
text = text.replace(
    'tagline_rect=QRectF(width * 0.20, height * 0.267, width * 0.60, height * 0.026),',
    'tagline_rect=QRectF(width * 0.20, height * 0.268, width * 0.60, height * 0.024),',
    1,
)
text = text.replace('context_top=height * 0.715,', 'context_top=height * 0.725,', 1)
frame.write_text(text)

# Supersede historical visual contracts from v5-v9. Functional behavior tests
# remain untouched; only assertions describing the discarded composition move
# to the approved v10 geometry.
replacements = {
    "tests/test_system_state_frame_v5.py": [
        ("test_portrait_v5_brand_icon_is_visible_and_separate_from_wordmark", "test_v10_brand_icon_is_visible_above_wordmark_inside_ring"),
        ("< radius * 0.72", "< radius * 0.82"),
    ],
    "tests/test_system_state_frame_v8.py": [
        ("test_v9_portrait_branding_is_present_without_colliding_with_status", "test_v10_portrait_branding_is_present_without_colliding_with_status"),
        ("assert width * 0.72 <= layout.hud_diameter <= width * 0.78", "assert width * 0.82 <= layout.hud_diameter <= width * 0.86"),
        ("assert layout.status_font_px >= layout.wordmark_font_px * 1.05", "assert layout.status_font_px < layout.wordmark_font_px"),
        ("test_v9_portrait_composition_has_clear_brand_status_context_zones", "test_v10_portrait_composition_has_clear_brand_status_context_zones"),
        ("assert layout.hud_center.y() <= height * 0.21", "assert height * 0.24 <= layout.hud_center.y() <= height * 0.26"),
        ("assert layout.context_top >= height * 0.70", "assert layout.context_top >= height * 0.72"),
        ("assert layout.floor_horizon >= height * 0.88", "assert layout.floor_horizon >= height * 0.86"),
    ],
    "tests/test_system_state_frame.py": [
        ("assert 480 * 0.70 <= layout.hud_diameter <= 480 * 0.80", "assert 480 * 0.82 <= layout.hud_diameter <= 480 * 0.86"),
        ("assert layout.status_font_px >= 480 * 0.13", "assert layout.status_font_px <= 480 * 0.075"),
        ("assert 480 * 0.82 <= layout.status_rect.width() <= 480 * 0.86", "assert 480 * 0.72 <= layout.status_rect.width() <= 480 * 0.76"),
        ("assert layout.status_rect.top() > layout.hud_center.y() + layout.hud_diameter / 2.0", "assert layout.status_rect.bottom() < layout.hud_center.y() + layout.hud_diameter / 2.0"),
        ("assert 480 * 0.60 <= layout.wordmark_rect.width() <= 480 * 0.68", "assert 480 * 0.78 <= layout.wordmark_rect.width() <= 480 * 0.82"),
        ("assert layout.wordmark_font_px < layout.status_font_px <= layout.wordmark_font_px * 1.35", "assert layout.status_font_px < layout.wordmark_font_px"),
        ("assert layout.status_rect.width() > layout.wordmark_rect.width()", "assert layout.status_rect.width() < layout.wordmark_rect.width()"),
        ("assert layout.hud_center.y() <= 1920 * 0.24", "assert 1920 * 0.24 <= layout.hud_center.y() <= 1920 * 0.26"),
        ("assert layout.status_rect.top() >= 1920 * 0.35", "assert layout.status_rect.bottom() < layout.hud_center.y() + layout.hud_diameter / 2.0"),
        ("assert layout.brand_icon_rect.bottom() + 480 * 0.018 <= layout.wordmark_rect.top()", "assert layout.brand_icon_rect.bottom() + 480 * 0.006 <= layout.wordmark_rect.top()"),
        ("assert layout.status_rect.bottom() < layout.bar_rect.top()", "assert layout.bar_rect.bottom() < layout.status_rect.top()"),
        ("< radius * 0.72", "< radius * 0.82"),
    ],
    "tests/test_system_state_orientation_polish.py": [
        ("assert layout.bar_rect.top() > layout.detail_rect.bottom()", "assert layout.bar_rect.bottom() < layout.status_rect.top()"),
    ],
    "tests/test_display_editor_native_zoom.py": [
        ("assert 480 * 0.60 <= layout.wordmark_rect.width() <= 480 * 0.68", "assert 480 * 0.78 <= layout.wordmark_rect.width() <= 480 * 0.82"),
    ],
}

for filename, pairs in replacements.items():
    path = Path(filename)
    text = path.read_text()
    for old, new in pairs:
        text = text.replace(old, new)
    path.write_text(text)

# v6 asserted legacy side-rail bridge pixels. v10 deliberately removes those
# rails, so the regression now verifies that the compact HUD itself renders and
# remains animated without depending on rail junctions.
v6 = Path("tests/test_system_state_frame_v6.py")
t = v6.read_text()
start = t.index("def test_v6_rail_ring_junctions_have_phase_independent_bridge_segments():")
replacement = '''def test_v10_compact_hud_animates_without_legacy_rail_bridges():\n    layout = _portrait_layout(480, 1920)\n    phase_a = _render(0.0)\n    phase_b = _render(0.5)\n\n    assert phase_a.size().width() == 480\n    assert phase_a.size().height() == 1920\n    assert phase_b.size() == phase_a.size()\n    assert bytes(phase_a.constBits()) != bytes(phase_b.constBits())\n    assert layout.hud_diameter >= 480 * 0.82\n'''
t = t[:start] + replacement + "\n"
v6.write_text(t)
