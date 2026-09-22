from pathlib import Path

PATH = Path("src/owndash/gui/system_state_frame.py")
text = PATH.read_text(encoding="utf-8")


def replace_between(source: str, start: str, end: str, replacement: str) -> str:
    a = source.index(start)
    b = source.index(end, a)
    return source[:a] + replacement.rstrip() + "\n\n" + source[b + 1 :]


layout = r'''def _portrait_layout(width: int, height: int) -> _PortraitLayout:
    """Geometry adapted from the approved master artwork for 480×1920 panels."""
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("portrait layout dimensions must be positive")

    # The approved artwork is much less top-heavy than v8-v11.  The ring is
    # deliberately smaller than the old 88%-width HUD and the status/clock
    # occupy their own vertical zones instead of being pulled toward it.
    center = QPointF(width * 0.50, height * 0.275)
    diameter = width * 0.72
    icon_side = width * 0.20
    return _PortraitLayout(
        hud_center=center,
        hud_diameter=diameter,
        brand_icon_rect=QRectF(
            width * 0.50 - icon_side / 2.0,
            height * 0.202,
            icon_side,
            icon_side,
        ),
        wordmark_rect=QRectF(width * 0.20, height * 0.285, width * 0.60, height * 0.047),
        wordmark_font_px=width * 0.102,
        tagline_rect=QRectF(width * 0.24, height * 0.336, width * 0.52, height * 0.018),
        separator_y=height * 0.393,
        state_icon_rect=QRectF(width * 0.40, height * 0.455, width * 0.20, height * 0.056),
        status_rect=QRectF(width * 0.15, height * 0.525, width * 0.70, height * 0.052),
        status_font_px=width * 0.112,
        detail_rect=QRectF(width * 0.14, height * 0.582, width * 0.72, height * 0.030),
        bar_rect=QRectF(width * 0.22, height * 0.635, width * 0.56, max(8.0, width * 0.016)),
        context_top=height * 0.720,
        floor_horizon=height * 0.845,
    )'''
text = replace_between(text, "def _portrait_layout", "\ndef _portrait_brand_icon_rect", layout)

hero = r'''def _draw_portrait_brand_hud(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    state: SystemState,
    phase: float,
) -> None:
    """Draw the luminous multi-layer hero ring from the approved artwork."""
    animated = state in _ANIMATED_STATES
    phase = (phase % 1.0) if animated else 0.0

    painter.save()
    # Deep cyan/magenta bloom behind the ring.  Separate side glows reproduce
    # the strong split-color atmosphere in the master artwork.
    for offset, color_name, alpha in (
        (-0.20, palette.cyan, 54),
        (0.20, palette.magenta, 48),
    ):
        gc = QPointF(center.x() + diameter * offset, center.y())
        glow = QRadialGradient(gc, diameter * 0.72)
        core = QColor(color_name)
        core.setAlpha(alpha)
        clear = QColor(color_name)
        clear.setAlpha(0)
        glow.setColorAt(0.0, core)
        glow.setColorAt(0.55, QColor(core.red(), core.green(), core.blue(), alpha // 3))
        glow.setColorAt(1.0, clear)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(gc.x() - diameter * 0.72, gc.y() - diameter * 0.72, diameter * 1.44, diameter * 1.44))

    structural = QColor(palette.secondary)
    painter.setBrush(Qt.NoBrush)
    for scale, alpha in ((1.06, 30), (0.96, 55), (0.82, 44), (0.68, 42)):
        d = diameter * scale
        structural.setAlpha(alpha)
        painter.setPen(QPen(structural, max(1.0, short * 0.0018)))
        painter.drawEllipse(QRectF(center.x() - d / 2.0, center.y() - d / 2.0, d, d))

    _draw_segmented_ring(
        painter, center, diameter * 0.985, short, palette,
        segments=10, coverage=0.62, width_scale=0.023,
        phase_degrees=phase * 30.0, alpha=255,
    )
    _draw_segmented_ring(
        painter, center, diameter * 0.835, short, palette,
        segments=16, coverage=0.31, width_scale=0.0075,
        phase_degrees=9.0 - phase * 24.0, alpha=205,
    )

    # Bright cardinal anchors like the master art.
    for degrees in (-90.0, 0.0, 90.0, 180.0):
        angle = math.radians(degrees)
        inner = diameter * 0.445
        outer = diameter * 0.535
        color = _neon_color_for_angle(palette, degrees)
        halo = QColor(color)
        halo.setAlpha(55)
        painter.setPen(QPen(halo, max(5.0, short * 0.015), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(
            QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner),
            QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer),
        )
        color.setAlpha(245)
        painter.setPen(QPen(color, max(1.5, short * 0.0045), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(
            QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner),
            QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer),
        )

    # Dotted technical inner guide.
    for index in range(36):
        angle = math.radians(index * 10.0 - 90.0)
        radius = diameter * 0.365
        point = QPointF(center.x() + math.cos(angle) * radius, center.y() + math.sin(angle) * radius)
        color = _neon_color_for_angle(palette, index * 10.0)
        color.setAlpha(185 if index % 2 == 0 else 90)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(point, max(0.8, short * 0.0021), max(0.8, short * 0.0021))
    painter.restore()'''
text = replace_between(text, "def _draw_portrait_brand_hud", "\ndef _draw_rail_ring_bridges", hero)

side_frame = r'''def _draw_reference_side_frame(painter: QPainter, width: int, height: int, short: float, palette: _Theme) -> None:
    """Draw the angular cyan/magenta enclosure visible in the approved artwork."""
    painter.save()
    for side, color_name in ((1, palette.cyan), (-1, palette.magenta)):
        color = QColor(color_name)
        color.setAlpha(238)
        direction = 1 if side > 0 else -1
        x_edge = width * (0.055 if side > 0 else 0.945)
        x_inner = width * (0.092 if side > 0 else 0.908)
        x_track = width * (0.073 if side > 0 else 0.927)

        main = QPainterPath(QPointF(x_edge, 0.0))
        main.lineTo(QPointF(x_edge, height * 0.040))
        main.lineTo(QPointF(x_inner, height * 0.070))
        main.lineTo(QPointF(x_inner, height * 0.145))
        main.lineTo(QPointF(x_track, height * 0.175))
        main.lineTo(QPointF(x_track, height * 0.705))
        main.lineTo(QPointF(x_inner, height * 0.735))
        main.lineTo(QPointF(x_inner, height * 0.825))
        main.lineTo(QPointF(x_edge, height * 0.855))
        main.lineTo(QPointF(x_edge, height * 0.925))

        glow = QColor(color)
        glow.setAlpha(48)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(glow, max(7.0, short * 0.023), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(main)
        painter.setPen(QPen(color, max(1.4, short * 0.0045), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(main)

        # Dark angular upper and lower pods with a faint inner rim.
        for y0, y1 in ((0.052, 0.150), (0.745, 0.835)):
            panel = QPainterPath(QPointF(0.0 if side > 0 else width, height * y0))
            panel.lineTo(QPointF(width * (0.028 if side > 0 else 0.972), height * y0))
            panel.lineTo(QPointF(width * (0.060 if side > 0 else 0.940), height * (y0 + 0.018)))
            panel.lineTo(QPointF(width * (0.060 if side > 0 else 0.940), height * (y1 - 0.018)))
            panel.lineTo(QPointF(width * (0.028 if side > 0 else 0.972), height * y1))
            panel.lineTo(QPointF(0.0 if side > 0 else width, height * y1))
            panel.closeSubpath()
            rim = QColor(color_name)
            rim.setAlpha(78)
            painter.setBrush(QColor(0, 3, 8, 215))
            painter.setPen(QPen(rim, max(1.0, short * 0.0022)))
            painter.drawPath(panel)

        dot_x = width * (0.036 if side > 0 else 0.964)
        for base in (0.078, 0.775):
            for idx in range(5):
                dot = QColor(color_name)
                dot.setAlpha(220 - idx * 10)
                painter.setPen(Qt.NoPen)
                painter.setBrush(dot)
                radius = max(1.3, short * 0.0048)
                painter.drawEllipse(QPointF(dot_x, height * base + idx * short * 0.034), radius, radius)
    painter.restore()'''
text = replace_between(text, "def _draw_reference_side_frame", "\ndef _draw_reference_separator", side_frame)

reference_helpers = r'''def _draw_reference_background(painter: QPainter, width: int, height: int, palette: _Theme) -> None:
    painter.save()
    top = QRadialGradient(QPointF(width * 0.50, height * 0.10), width * 0.78)
    core = QColor(palette.cyan)
    core.setAlpha(34)
    clear = QColor(palette.cyan)
    clear.setAlpha(0)
    top.setColorAt(0.0, core)
    top.setColorAt(1.0, clear)
    painter.setPen(Qt.NoPen)
    painter.setBrush(top)
    painter.drawEllipse(QRectF(-width * 0.28, -height * 0.05, width * 1.56, width * 1.48))

    for x, color_name in ((width * 0.04, palette.cyan), (width * 0.96, palette.magenta)):
        side = QRadialGradient(QPointF(x, height * 0.50), width * 0.55)
        color = QColor(color_name)
        color.setAlpha(18)
        transparent = QColor(color_name)
        transparent.setAlpha(0)
        side.setColorAt(0.0, color)
        side.setColorAt(1.0, transparent)
        painter.setBrush(side)
        painter.drawEllipse(QRectF(x - width * 0.55, height * 0.22, width * 1.10, height * 0.56))
    painter.restore()


def _draw_reference_wordmark(painter: QPainter, image: QImage, rect: QRectF, palette: _Theme, px: float) -> None:
    font = _fit_single_line_font(image, APP_NAME, rect, px, bold=True, family="DejaVu Sans")
    painter.save()
    painter.setFont(font)
    metrics = QFontMetricsF(font, image)
    bounds = metrics.boundingRect(APP_NAME)
    x = rect.center().x() - bounds.width() / 2.0 - bounds.left()
    y = rect.center().y() + (metrics.ascent() - metrics.descent()) / 2.0
    path = QPainterPath()
    path.addText(QPointF(x, y), font, APP_NAME)
    grad = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    grad.setColorAt(0.0, QColor(palette.cyan))
    grad.setColorAt(0.48, QColor("#6b7cff"))
    grad.setColorAt(1.0, QColor(palette.magenta))
    for width_scale, opacity in ((12.0, 0.10), (7.0, 0.18), (3.5, 0.32)):
        painter.setOpacity(opacity)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QBrush(grad), width_scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
    painter.setOpacity(1.0)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(grad))
    painter.drawPath(path)
    painter.restore()


def _draw_reference_separator(painter: QPainter, width: int, y: float, short: float, palette: _Theme) -> None:
    gradient = QLinearGradient(width * 0.25, y, width * 0.75, y)
    gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
    gradient.setColorAt(0.35, QColor(palette.cyan))
    gradient.setColorAt(0.50, QColor("#eafcff"))
    gradient.setColorAt(0.65, QColor(palette.magenta))
    gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.save()
    painter.setOpacity(0.20)
    painter.setPen(QPen(QBrush(gradient), max(8.0, short * 0.020), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.25, y), QPointF(width * 0.75, y))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(gradient), max(1.3, short * 0.0035), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.25, y), QPointF(width * 0.75, y))
    painter.restore()


def _draw_reference_headline(
    painter: QPainter,
    image: QImage,
    rect: QRectF,
    text: str,
    px: float,
    palette: _Theme,
    accent: QColor,
) -> None:
    # Wide tracking is a defining feature of the approved artwork.  Reduce
    # tracking first and then font size for long words such as HERUNTERFAHREN.
    spacing = max(1.0, rect.width() * (0.014 if len(text) <= 9 else 0.006))
    font = QFont("DejaVu Sans")
    font.setWeight(QFont.Weight.Medium)
    font.setPixelSize(max(1, round(px)))
    while font.pixelSize() > 17:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        metrics = QFontMetricsF(font, image)
        if metrics.horizontalAdvance(text) <= rect.width() * 0.98 and metrics.height() <= rect.height():
            break
        if spacing > 1.2:
            spacing = max(1.0, spacing - 0.45)
        else:
            font.setPixelSize(font.pixelSize() - 1)
    painter.save()
    painter.setFont(font)
    flags = Qt.AlignCenter | Qt.AlignVCenter
    glow = QColor(accent)
    for dx, dy, alpha in ((-2, 0, 22), (2, 0, 22), (0, -2, 18), (0, 2, 18), (-1, 0, 42), (1, 0, 42)):
        glow.setAlpha(alpha)
        painter.setPen(glow)
        painter.drawText(rect.translated(dx, dy), flags, text)
    painter.setPen(QColor(palette.primary))
    painter.drawText(rect, flags, text)
    painter.restore()


def _draw_reference_progress_bar(painter: QPainter, rect: QRectF, palette: _Theme, state: SystemState) -> None:
    painter.save()
    y = rect.center().y()
    track = QLinearGradient(rect.left(), y, rect.right(), y)
    left = QColor(palette.cyan); left.setAlpha(150)
    right = QColor(palette.magenta); right.setAlpha(150)
    track.setColorAt(0.0, left)
    track.setColorAt(0.5, QColor(80, 115, 165, 95))
    track.setColorAt(1.0, right)
    painter.setPen(QPen(QBrush(track), max(1.2, rect.height() * 0.16), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    active_left = rect.left() + rect.width() * 0.20
    active_right = rect.right() - rect.width() * 0.20
    active = QLinearGradient(active_left, y, active_right, y)
    active.setColorAt(0.0, QColor(palette.cyan))
    active.setColorAt(0.52, QColor("#5c89ff"))
    active.setColorAt(1.0, QColor(palette.magenta))
    painter.setOpacity(0.16)
    painter.setPen(QPen(QBrush(active), max(10.0, rect.height() * 1.8), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(active_left, y), QPointF(active_right, y))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(active), max(4.0, rect.height() * 0.62), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(active_left, y), QPointF(active_right, y))
    painter.restore()


def _draw_reference_floor(painter: QPainter, width: int, height: int, short: float, palette: _Theme, horizon: float) -> None:
    """Draw the bright curved podium and reflective grid from the master art."""
    painter.save()
    # Curved podium cap.
    cap = QPainterPath(QPointF(width * 0.11, horizon + short * 0.016))
    cap.quadTo(QPointF(width * 0.50, horizon - short * 0.026), QPointF(width * 0.89, horizon + short * 0.016))
    cap.lineTo(QPointF(width * 0.86, height * 0.925))
    cap.lineTo(QPointF(width * 0.14, height * 0.925))
    cap.closeSubpath()
    fill = QLinearGradient(0, horizon, 0, height * 0.925)
    fill.setColorAt(0.0, QColor(10, 28, 48, 205))
    fill.setColorAt(1.0, QColor(1, 5, 12, 235))
    painter.setBrush(fill)
    painter.setPen(Qt.NoPen)
    painter.drawPath(cap)

    rim = QLinearGradient(width * 0.11, horizon, width * 0.89, horizon)
    rim.setColorAt(0.0, QColor(palette.cyan))
    rim.setColorAt(0.48, QColor("#f7ffff"))
    rim.setColorAt(1.0, QColor(palette.magenta))
    painter.setBrush(Qt.NoBrush)
    painter.setOpacity(0.18)
    painter.setPen(QPen(QBrush(rim), max(10.0, short * 0.024), Qt.SolidLine, Qt.RoundCap))
    painter.drawPath(QPainterPath(cap))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(rim), max(1.5, short * 0.004), Qt.SolidLine, Qt.RoundCap))
    top_line = QPainterPath(QPointF(width * 0.11, horizon + short * 0.016))
    top_line.quadTo(QPointF(width * 0.50, horizon - short * 0.026), QPointF(width * 0.89, horizon + short * 0.016))
    painter.drawPath(top_line)

    # Podium divisions.
    for x_ratio, color_name in ((0.33, palette.cyan), (0.50, "#7fefff"), (0.67, palette.magenta)):
        color = QColor(color_name); color.setAlpha(155)
        painter.setPen(QPen(color, max(1.0, short * 0.0026)))
        painter.drawLine(QPointF(width * x_ratio, horizon), QPointF(width * x_ratio, height * 0.925))

    # Reflective floor beneath the podium.
    floor_top = height * 0.925
    for y_ratio, alpha in ((0.940, 70), (0.958, 55), (0.976, 42), (0.992, 30)):
        grad = QLinearGradient(0, 0, width, 0)
        c1 = QColor(palette.cyan); c1.setAlpha(alpha)
        c2 = QColor(palette.magenta); c2.setAlpha(alpha)
        grad.setColorAt(0.0, c1); grad.setColorAt(0.5, QColor(90, 235, 255, alpha // 2)); grad.setColorAt(1.0, c2)
        painter.setPen(QPen(QBrush(grad), max(1.0, short * 0.0018)))
        painter.drawLine(QPointF(0, height * y_ratio), QPointF(width, height * y_ratio))

    vanish = QPointF(width * 0.50, floor_top)
    for bottom_x, color_name in ((0.0, palette.cyan), (0.20, palette.cyan), (0.50, "#7fefff"), (0.80, palette.magenta), (1.0, palette.magenta)):
        color = QColor(color_name); color.setAlpha(70)
        painter.setPen(QPen(color, max(1.0, short * 0.0017)))
        painter.drawLine(vanish, QPointF(width * bottom_x, height))

    glow = QRadialGradient(QPointF(width * 0.50, height * 0.965), width * 0.42)
    gc = QColor(palette.cyan); gc.setAlpha(42)
    gm = QColor(palette.magenta); gm.setAlpha(22)
    clear = QColor(0, 0, 0, 0)
    glow.setColorAt(0.0, gc); glow.setColorAt(0.52, gm); glow.setColorAt(1.0, clear)
    painter.setPen(Qt.NoPen); painter.setBrush(glow)
    painter.drawEllipse(QRectF(width * 0.08, floor_top - short * 0.05, width * 0.84, height - floor_top + short * 0.10))
    painter.restore()'''
text = replace_between(text, "def _draw_reference_separator", "\ndef _draw_state_icon", reference_helpers)

portrait_block = r'''    if portrait:
        layout = _portrait_layout(width, height)
        headline, state_detail = _portrait_state_copy(state, title, detail)

        _draw_reference_background(painter, width, height, palette)
        _draw_reference_side_frame(painter, width, height, short, palette)
        _draw_portrait_brand_hud(
            painter, layout.hud_center, layout.hud_diameter, short, palette, state, phase
        )
        _draw_brand_icon(painter, icon, layout.brand_icon_rect, short, palette)
        _draw_reference_wordmark(
            painter, image, layout.wordmark_rect, palette, layout.wordmark_font_px
        )

        _draw_reference_separator(painter, width, layout.separator_y, short, palette)
        _draw_state_icon(painter, layout.state_icon_rect, state, palette, short)
        accent = QColor(_STATE_ACCENTS[state])
        _draw_reference_headline(
            painter, image, layout.status_rect, headline, layout.status_font_px, palette, accent
        )
        _draw_centered_single_line(
            painter, image, layout.detail_rect, state_detail, width * 0.040,
            palette.secondary, bold=False, family="DejaVu Sans"
        )
        _draw_reference_progress_bar(painter, layout.bar_rect, palette, state)

        context_y = layout.context_top
        if clock_text:
            _draw_centered_single_line(
                painter, image, QRectF(width * 0.17, context_y, width * 0.66, height * 0.062),
                clock_text, width * 0.122, palette.primary, bold=False, glow=palette.cyan,
                family="DejaVu Sans"
            )
        if date_text:
            _draw_centered_single_line(
                painter, image, QRectF(width * 0.19, context_y + height * 0.064, width * 0.62, height * 0.030),
                date_text, width * 0.041, palette.secondary, family="DejaVu Sans"
            )

        _draw_reference_floor(painter, width, height, short, palette, layout.floor_horizon)
        footer = f"{APP_NAME} {__version__}"
        _draw_centered_single_line(
            painter, image, QRectF(width * 0.17, height * 0.886, width * 0.66, height * 0.025),
            footer, width * 0.026, palette.muted, family="DejaVu Sans"
        )'''
text = replace_between(text, "    if portrait:\n", "\n    else:\n", portrait_block)

PATH.write_text(text, encoding="utf-8")
print("Applied approved master-reference portrait renderer")
