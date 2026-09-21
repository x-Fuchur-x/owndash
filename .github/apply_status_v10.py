from pathlib import Path

path = Path("src/owndash/gui/system_state_frame.py")
text = path.read_text()

old_fields = '''    hud_center: QPointF\n    hud_diameter: float\n    brand_icon_rect: QRectF\n    wordmark_rect: QRectF\n    wordmark_font_px: float\n    status_panel_rect: QRectF\n    status_icon_rect: QRectF\n    status_rect: QRectF\n    status_font_px: float\n    detail_rect: QRectF\n    detail_font_px: float\n    bar_rect: QRectF\n    progress_label_rect: QRectF\n    context_top: float\n    floor_horizon: float\n'''
new_fields = '''    hud_center: QPointF\n    hud_diameter: float\n    brand_icon_rect: QRectF\n    wordmark_rect: QRectF\n    wordmark_font_px: float\n    tagline_rect: QRectF\n    bar_rect: QRectF\n    status_rect: QRectF\n    status_font_px: float\n    context_top: float\n    floor_horizon: float\n'''
if old_fields not in text:
    raise SystemExit("v9 portrait dataclass not found")
text = text.replace(old_fields, new_fields, 1)

start = text.index("def _portrait_layout(width: int, height: int) -> _PortraitLayout:")
end = text.index("\ndef _portrait_brand_icon_rect", start)
new_layout = '''def _portrait_layout(width: int, height: int) -> _PortraitLayout:\n    """Return the approved v10 portrait composition for 480×1920 case displays."""\n    width = int(width)\n    height = int(height)\n    if width <= 0 or height <= 0:\n        raise ValueError("portrait layout dimensions must be positive")\n\n    # v10 mirrors the approved reference: one compact hero instrument contains\n    # the complete OwnDash identity and the current system state. The footer is\n    # deliberately separate, leaving clean negative space instead of the old\n    # tall framed status channel.\n    center = QPointF(width * 0.50, height * 0.250)\n    diameter = width * 0.84\n    icon_side = width * 0.20\n    return _PortraitLayout(\n        hud_center=center,\n        hud_diameter=diameter,\n        brand_icon_rect=QRectF(\n            width * 0.50 - icon_side / 2.0,\n            height * 0.166,\n            icon_side,\n            icon_side,\n        ),\n        wordmark_rect=QRectF(width * 0.10, height * 0.218, width * 0.80, height * 0.055),\n        wordmark_font_px=width * 0.128,\n        tagline_rect=QRectF(width * 0.20, height * 0.267, width * 0.60, height * 0.026),\n        bar_rect=QRectF(width * 0.225, height * 0.301, width * 0.55, max(7.0, width * 0.016)),\n        status_rect=QRectF(width * 0.13, height * 0.318, width * 0.74, height * 0.038),\n        status_font_px=width * 0.060,\n        context_top=height * 0.715,\n        floor_horizon=height * 0.875,\n    )\n'''
text = text[:start] + new_layout + text[end:]

# Replace only the portrait rendering branch. The landscape renderer and all
# state-detection/runtime behavior remain untouched.
portrait_start = text.index("    if portrait:\n")
portrait_end = text.index("    else:\n", portrait_start)
new_portrait = '''    if portrait:\n        layout = _portrait_layout(width, height)\n\n        # Approved v10 hero: no legacy side rails and no separate status panel.\n        # All brand/state information lives inside one instrument, matching the\n        # accepted preview and the supplied neon HUD reference.\n        _draw_portrait_brand_hud(\n            painter,\n            layout.hud_center,\n            layout.hud_diameter,\n            short,\n            palette,\n            state,\n            phase,\n        )\n        _draw_brand_icon(painter, icon, layout.brand_icon_rect, short, palette)\n        _draw_gradient_wordmark(\n            painter, image, layout.wordmark_rect, palette, layout.wordmark_font_px\n        )\n\n        # Fine technical subline, deliberately quieter than the OwnDash mark.\n        subline_color = QColor(palette.secondary)\n        subline_color.setAlpha(225)\n        line_y = layout.tagline_rect.center().y()\n        painter.setPen(QPen(QColor(palette.cyan), max(1.0, short * 0.0022), Qt.SolidLine, Qt.RoundCap))\n        painter.drawLine(\n            QPointF(width * 0.13, line_y),\n            QPointF(layout.tagline_rect.left() - width * 0.025, line_y),\n        )\n        painter.setPen(QPen(QColor(palette.magenta), max(1.0, short * 0.0022), Qt.SolidLine, Qt.RoundCap))\n        painter.drawLine(\n            QPointF(layout.tagline_rect.right() + width * 0.025, line_y),\n            QPointF(width * 0.87, line_y),\n        )\n        _draw_centered_single_line(\n            painter,\n            image,\n            layout.tagline_rect,\n            "PC DASHBOARD SYSTEM",\n            width * 0.027,\n            subline_color.name(),\n            family="DejaVu Sans",\n        )\n\n        # The slim state rail and sentence-case state label reproduce the\n        # accepted reference hierarchy. Long localized labels shrink smoothly\n        # instead of becoming an oversized block headline.\n        _draw_state_rail(painter, layout.bar_rect, palette, state, phase)\n        accent = QColor(_STATE_ACCENTS[state])\n        _draw_centered_single_line(\n            painter,\n            image,\n            layout.status_rect,\n            title,\n            layout.status_font_px,\n            palette.primary,\n            bold=False,\n            glow=accent.name(),\n            family="DejaVu Sans",\n        )\n\n        # Quiet footer: readable time/date plus the subtle illuminated floor\n        # from the reference. No tall rails or old status channel return here.\n        context_y = layout.context_top\n        if clock_text:\n            _draw_centered_single_line(\n                painter,\n                image,\n                QRectF(width * 0.16, context_y, width * 0.68, height * 0.050),\n                clock_text,\n                width * 0.105,\n                palette.primary,\n                bold=True,\n                glow=palette.cyan,\n                family="DejaVu Sans Condensed",\n            )\n        if date_text:\n            _draw_centered_single_line(\n                painter,\n                image,\n                QRectF(width * 0.20, context_y + height * 0.055, width * 0.60, height * 0.025),\n                date_text,\n                width * 0.032,\n                palette.secondary,\n                family="DejaVu Sans",\n            )\n\n        # Minimal horizon glow and reflection; the legacy framed side structure\n        # is intentionally absent in v10.\n        _draw_floor_reflection(painter, width, height, short, palette, layout.floor_horizon)\n\n        footer = f"{APP_NAME} · {__version__}"\n        _draw_centered_single_line(\n            painter,\n            image,\n            QRectF(width * 0.20, height * 0.965, width * 0.60, height * 0.018),\n            footer,\n            width * 0.018,\n            palette.muted,\n            family="DejaVu Sans",\n        )\n'''
text = text[:portrait_start] + new_portrait + text[portrait_end:]

path.write_text(text)

# Supersede only old visual-contract assertions that describe v8/v9 geometry.
# Functional rendering/state tests are intentionally left unchanged.
visual_files = [
    Path("tests/test_system_state_frame_v9.py"),
    Path("tests/test_system_state_frame_v8.py"),
    Path("tests/test_system_state_orientation_polish.py"),
    Path("tests/test_display_editor_native_zoom.py"),
    Path("tests/test_system_state_frame.py"),
]
for test_path in visual_files:
    if not test_path.exists():
        continue
    t = test_path.read_text()
    # v9 panel fields are gone in the approved v10 composition.
    if test_path.name == "test_system_state_frame_v9.py":
        t = t.replace("def test_v9_portrait_uses_separate_brand_status_and_context_zones():", "def test_v10_portrait_uses_compact_hero_and_separate_context_zone():")
        t = t.replace("assert layout.status_rect.top() >= 1920 * 0.50", "assert layout.status_rect.top() < 1920 * 0.40")
        t = t.replace("def test_v9_layout_reserves_state_icon_panel_and_progress_caption():\n    layout = _portrait_layout(480, 1920)\n\n    assert isinstance(layout.status_panel_rect, QRectF)\n    assert isinstance(layout.status_icon_rect, QRectF)\n    assert isinstance(layout.progress_label_rect, QRectF)\n    assert layout.status_panel_rect.contains(layout.status_icon_rect)\n    assert layout.status_panel_rect.contains(layout.status_rect)\n    assert layout.status_panel_rect.bottom() < layout.context_top\n\n\n", "")
        t = t.replace("test_v9_long_terminal_title_fits_status_width_without_touching_edges", "test_v10_long_terminal_title_fits_status_width_without_touching_edges")
        t = t.replace("_fit_font(QImage(480, 1920, QImage.Format_RGB32), title, safe_rect, layout.status_font_px, bold=True)", "_fit_single_line_font(QImage(480, 1920, QImage.Format_RGB32), title, safe_rect, layout.status_font_px, bold=False)")
        t = t.replace("from owndash.gui.system_state_frame import _fit_font, _portrait_layout, render_system_state_image", "from owndash.gui.system_state_frame import _fit_single_line_font, _portrait_layout, render_system_state_image")
        t = t.replace("test_v9_every_supported_state_still_renders_at_native_portrait_size", "test_v10_every_supported_state_still_renders_at_native_portrait_size")
    # Known geometry contracts from previous designs: move them to v10 values.
    t = t.replace("assert layout.status_rect.top() >= height * 0.50", "assert layout.status_rect.top() < height * 0.40")
    t = t.replace("assert layout.status_rect.top() >= height * 0.36", "assert layout.status_rect.top() < height * 0.40")
    t = t.replace("assert layout.bar_rect.bottom() <= height * 0.66", "assert layout.bar_rect.bottom() <= height * 0.33")
    t = t.replace("assert layout.context_top >= height * 0.70", "assert layout.context_top >= height * 0.70")
    t = t.replace("assert width * 0.72 <= layout.hud_diameter <= width * 0.78", "assert width * 0.82 <= layout.hud_diameter <= width * 0.86")
    t = t.replace("assert layout.hud_diameter <= width * 0.80", "assert layout.hud_diameter <= width * 0.86")
    t = t.replace("assert layout.status_font_px >= layout.wordmark_font_px * 1.25", "assert layout.status_font_px < layout.wordmark_font_px")
    t = t.replace("assert layout.status_font_px >= layout.wordmark_font_px * 1.05", "assert layout.status_font_px < layout.wordmark_font_px")
    t = t.replace("assert layout.status_font_px > layout.wordmark_font_px", "assert layout.status_font_px < layout.wordmark_font_px")
    t = t.replace("assert layout.status_font_px <= layout.wordmark_font_px * 1.35", "assert layout.status_font_px <= layout.wordmark_font_px")
    t = t.replace("assert layout.status_rect.top() >= (\n        layout.hud_center.y() + layout.hud_diameter / 2.0 + height * 0.02\n    )", "assert layout.status_rect.bottom() < layout.hud_center.y() + layout.hud_diameter / 2.0")
    t = t.replace("assert layout.detail_rect.top() >= layout.status_rect.bottom()", "assert layout.status_rect.bottom() < layout.hud_center.y() + layout.hud_diameter / 2.0")
    t = t.replace("assert layout.detail_rect.bottom() <= layout.bar_rect.top()", "assert layout.wordmark_rect.bottom() < layout.bar_rect.top()")
    t = t.replace("assert layout.wordmark_rect.bottom() < layout.status_rect.top()", "assert layout.wordmark_rect.bottom() < layout.status_rect.top()")
    test_path.write_text(t)
