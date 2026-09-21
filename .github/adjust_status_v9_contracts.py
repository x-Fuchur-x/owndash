from pathlib import Path

# The main v9 patch has already transformed the renderer in the workflow
# workspace. This small second pass aligns deliberately superseded v8 visual
# contracts and strengthens the status-vs-brand hierarchy.
frame = Path("src/owndash/gui/system_state_frame.py")
text = frame.read_text()
text = text.replace("status_font_px=width * 0.150,", "status_font_px=width * 0.160,", 1)
text = text.replace(
    "detail_rect=QRectF(width * 0.12, height * 0.585, width * 0.76, height * 0.036),",
    "detail_rect=QRectF(width * 0.12, height * 0.590, width * 0.76, height * 0.036),",
    1,
)
frame.write_text(text)

path = Path("tests/test_display_editor_native_zoom.py")
text = path.read_text()
text = text.replace(
    "assert layout.wordmark_rect.width() >= 480 * 0.76",
    "assert 480 * 0.60 <= layout.wordmark_rect.width() <= 480 * 0.68",
)
path.write_text(text)

path = Path("tests/test_system_state_frame.py")
text = path.read_text()
text = text.replace(
    "assert layout.status_rect.width() >= 480 * 0.90",
    "assert 480 * 0.82 <= layout.status_rect.width() <= 480 * 0.86",
)
path.write_text(text)

path = Path("tests/test_system_state_frame_v8.py")
text = path.read_text()
text = text.replace("test_v8_portrait_branding_is_more_present_but_status_stays_primary", "test_v9_portrait_branding_is_present_without_colliding_with_status")
text = text.replace("assert layout.hud_diameter <= width * 0.70", "assert width * 0.72 <= layout.hud_diameter <= width * 0.78")
text = text.replace("assert layout.wordmark_font_px >= width * 0.14", "assert width * 0.12 <= layout.wordmark_font_px <= width * 0.13")
text = text.replace("test_v8_portrait_composition_has_clear_brand_status_context_zones", "test_v9_portrait_composition_has_clear_brand_status_context_zones")
text = text.replace("assert layout.hud_center.y() <= height * 0.20", "assert layout.hud_center.y() <= height * 0.21")
text = text.replace("assert layout.status_rect.top() >= height * 0.36", "assert layout.status_rect.top() >= height * 0.50")
text = text.replace("assert layout.bar_rect.bottom() <= height * 0.56", "assert layout.bar_rect.bottom() <= height * 0.66")
text = text.replace("assert layout.context_top >= height * 0.62", "assert layout.context_top >= height * 0.70")
text = text.replace("assert layout.floor_horizon >= height * 0.84", "assert layout.floor_horizon >= height * 0.88")
text = text.replace("test_v8_portrait_layout_drops_decorative_telemetry_tick_band", "test_v9_portrait_layout_keeps_telemetry_tick_band_removed")
path.write_text(text)
