from pathlib import Path

path = Path("src/owndash/gui/system_state_frame.py")
text = path.read_text()

text = text.replace(
    "    context_top: float\n    telemetry_y: float\n    floor_horizon: float\n",
    "    context_top: float\n    floor_horizon: float\n",
)

start = text.index("def _portrait_layout(width: int, height: int) -> _PortraitLayout:")
end = text.index("\ndef _portrait_brand_icon_rect", start)
new_layout = '''def _portrait_layout(width: int, height: int) -> _PortraitLayout:
    """Return the v8 portrait composition for narrow auxiliary displays."""
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("portrait layout dimensions must be positive")

    # v8 uses three calm vertical zones: OwnDash identity, system state, context.
    # Branding is deliberately stronger than v7, while the state remains the
    # largest text element and the lower third gets substantially more air.
    center = QPointF(width * 0.50, height * 0.185)
    diameter = width * 0.70
    icon_side = width * 0.20
    icon_center = QPointF(center.x(), center.y() - diameter * 0.175)
    brand_icon_rect = QRectF(
        icon_center.x() - icon_side / 2.0,
        icon_center.y() - icon_side / 2.0,
        icon_side,
        icon_side,
    )
    return _PortraitLayout(
        hud_center=center,
        hud_diameter=diameter,
        brand_icon_rect=brand_icon_rect,
        wordmark_rect=QRectF(width * 0.09, center.y() + height * 0.006, width * 0.82, height * 0.060),
        wordmark_font_px=width * 0.145,
        status_rect=QRectF(width * 0.04, height * 0.365, width * 0.92, height * 0.095),
        status_font_px=width * 0.183,
        detail_rect=QRectF(width * 0.10, height * 0.465, width * 0.80, height * 0.040),
        detail_font_px=width * 0.034,
        bar_rect=QRectF(width * 0.21, height * 0.520, width * 0.58, max(8.0, width * 0.018)),
        context_top=height * 0.635,
        floor_horizon=height * 0.855,
    )
'''
text = text[:start] + new_layout + text[end:]

marker = "\ndef _draw_rail_ring_bridges("
idx = text.index(marker)
helper = '''
def _draw_portrait_brand_hud(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    state: SystemState,
    phase: float,
) -> None:
    """Draw the calmer v8 identity ring used on portrait status screens."""
    animated = state in _ANIMATED_STATES
    phase = (phase % 1.0) if animated else 0.0

    glow = QRadialGradient(center, diameter * 0.60)
    glow_core = QColor(palette.cyan)
    glow_core.setAlpha(24)
    glow_mid = QColor(palette.magenta)
    glow_mid.setAlpha(9)
    clear = QColor(0, 0, 0, 0)
    glow.setColorAt(0.0, glow_core)
    glow.setColorAt(0.58, glow_mid)
    glow.setColorAt(1.0, clear)
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QRectF(
        center.x() - diameter * 0.60,
        center.y() - diameter * 0.60,
        diameter * 1.20,
        diameter * 1.20,
    ))

    guide = QColor(palette.secondary)
    guide.setAlpha(34)
    painter.setBrush(Qt.NoBrush)
    inner = diameter * 0.70
    painter.setPen(QPen(guide, max(1.0, short * 0.0018)))
    painter.drawEllipse(QRectF(center.x() - inner / 2, center.y() - inner / 2, inner, inner))

    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.988,
        short,
        palette,
        segments=8,
        coverage=0.72,
        width_scale=0.016,
        phase_degrees=phase * 72.0,
        alpha=238,
    )

'''
text = text[:idx] + helper + text[idx:]

start = text.index("def _draw_floor_reflection(")
end = text.index("\ndef _draw_state_rail", start)
new_floor = '''def _draw_floor_reflection(
    painter: QPainter,
    width: int,
    height: int,
    short: float,
    palette: _Theme,
    *,
    horizon: float | None = None,
) -> None:
    """Draw a restrained v8 lower light reflection without perspective grid."""
    horizon = float(height * 0.855 if horizon is None else horizon)
    line_gradient = QLinearGradient(width * 0.08, horizon, width * 0.92, horizon)
    line_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
    cyan = QColor(palette.cyan)
    green = QColor(palette.green)
    magenta = QColor(palette.magenta)
    cyan.setAlpha(190)
    green.setAlpha(135)
    magenta.setAlpha(190)
    line_gradient.setColorAt(0.24, cyan)
    line_gradient.setColorAt(0.50, green)
    line_gradient.setColorAt(0.76, magenta)
    line_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

    painter.save()
    painter.setOpacity(0.11)
    painter.setPen(QPen(QBrush(line_gradient), max(7.0, short * 0.020), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.10, horizon), QPointF(width * 0.90, horizon))
    painter.setOpacity(0.90)
    painter.setPen(QPen(QBrush(line_gradient), max(2.0, short * 0.0040), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.10, horizon), QPointF(width * 0.90, horizon))

    for x_ratio, color_name, alpha in (
        (0.30, palette.cyan, 48),
        (0.50, palette.green, 32),
        (0.70, palette.magenta, 48),
    ):
        glow = QRadialGradient(QPointF(width * x_ratio, horizon + short * 0.08), short * 0.42)
        color = QColor(color_name)
        color.setAlpha(alpha)
        clear = QColor(color_name)
        clear.setAlpha(0)
        glow.setColorAt(0.0, color)
        glow.setColorAt(1.0, clear)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(
            width * x_ratio - short * 0.42,
            horizon - short * 0.03,
            short * 0.84,
            short * 0.62,
        ))

    for x_ratio, color_name in ((0.31, palette.cyan), (0.50, palette.green), (0.69, palette.magenta)):
        color = QColor(color_name)
        color.setAlpha(110)
        fade = QLinearGradient(0, horizon, 0, horizon + short * 0.38)
        fade.setColorAt(0.0, color)
        tail = QColor(color_name)
        tail.setAlpha(0)
        fade.setColorAt(1.0, tail)
        painter.setPen(QPen(QBrush(fade), max(2.0, short * 0.007), Qt.SolidLine, Qt.RoundCap))
        x = width * x_ratio
        painter.drawLine(QPointF(x, horizon), QPointF(x, min(height, horizon + short * 0.38)))
    painter.restore()

'''
text = text[:start] + new_floor + text[end:]

text = text.replace(
    "        _draw_hud_rings(painter, layout.hud_center, layout.hud_diameter, short, palette, state, phase)\n",
    "        _draw_portrait_brand_hud(painter, layout.hud_center, layout.hud_diameter, short, palette, state, phase)\n",
)

status_label = '''        _draw_centered(
            painter,
            image,
            QRectF(width * 0.20, layout.hud_center.y() + height * 0.038, width * 0.60, height * 0.022),
            "SYSTEM STATUS",
            width * 0.021,
            palette.secondary,
            family="DejaVu Sans Condensed",
        )

'''
text = text.replace(status_label, "")

tick_start = text.index("        for index in range(11):\n", text.index("    if portrait:"))
tick_end = text.index("\n        _draw_floor_reflection", tick_start)
text = text[:tick_start] + text[tick_end:]

path.write_text(text)

# v8 intentionally supersedes the old v7 visual-contract ranges while keeping
# all functional, orientation and rail-continuity assertions untouched.
tests_path = Path("tests/test_system_state_frame.py")
tests = tests_path.read_text()
tests = tests.replace(
    "assert 480 * 0.11 <= layout.wordmark_font_px <= 480 * 0.125",
    "assert 480 * 0.14 <= layout.wordmark_font_px <= 480 * 0.15",
)
tests = tests.replace(
    "assert 1920 * 0.55 <= layout.context_top <= 1920 * 0.60",
    "assert 1920 * 0.62 <= layout.context_top <= 1920 * 0.66",
)
tests_path.write_text(tests)
