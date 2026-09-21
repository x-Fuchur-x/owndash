from pathlib import Path
import re

path = Path('src/owndash/gui/system_state_frame.py')
text = path.read_text()

text = text.replace(
'''    tagline_rect: QRectF
    bar_rect: QRectF
    status_rect: QRectF
    status_font_px: float
    context_top: float
    floor_horizon: float
''',
'''    tagline_rect: QRectF
    separator_y: float
    state_icon_rect: QRectF
    status_rect: QRectF
    status_font_px: float
    detail_rect: QRectF
    bar_rect: QRectF
    context_top: float
    floor_horizon: float
''')

old_layout = re.compile(r'def _portrait_layout\(width: int, height: int\) -> _PortraitLayout:\n.*?\n\ndef _portrait_brand_icon_rect', re.S)
new_layout = '''def _portrait_layout(width: int, height: int) -> _PortraitLayout:
    """Geometry derived from the approved portrait reference image."""
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("portrait layout dimensions must be positive")

    center = QPointF(width * 0.50, height * 0.235)
    diameter = width * 0.88
    icon_side = width * 0.235
    return _PortraitLayout(
        hud_center=center,
        hud_diameter=diameter,
        brand_icon_rect=QRectF(
            width * 0.50 - icon_side / 2.0,
            height * 0.165,
            icon_side,
            icon_side,
        ),
        wordmark_rect=QRectF(width * 0.10, height * 0.242, width * 0.80, height * 0.050),
        wordmark_font_px=width * 0.135,
        tagline_rect=QRectF(width * 0.22, height * 0.296, width * 0.56, height * 0.020),
        separator_y=height * 0.356,
        state_icon_rect=QRectF(width * 0.405, height * 0.382, width * 0.19, height * 0.060),
        status_rect=QRectF(width * 0.075, height * 0.452, width * 0.85, height * 0.060),
        status_font_px=width * 0.103,
        detail_rect=QRectF(width * 0.12, height * 0.516, width * 0.76, height * 0.032),
        bar_rect=QRectF(width * 0.245, height * 0.574, width * 0.51, max(7.0, width * 0.015)),
        context_top=height * 0.672,
        floor_horizon=height * 0.885,
    )

def _portrait_brand_icon_rect'''
text, count = old_layout.subn(new_layout, text, count=1)
assert count == 1, f'layout replacement count={count}'

anchor = '\ndef _draw_state_icon(\n'
helpers = '''

def _portrait_state_copy(state: SystemState, title: str, detail: str) -> tuple[str, str]:
    """Turn localized runtime copy into the approved compact reference copy."""
    lowered = title.strip().lower()
    english = any(token in lowered for token in ("locked", "shutting", "restart", "transition", "idle"))
    if state is SystemState.LOCKED:
        return ("LOCKED", "System is locked") if english else ("GESPERRT", "System ist gesperrt")
    if state is SystemState.SHUTTING_DOWN:
        return ("SHUTTING DOWN", "System is shutting down safely") if english else ("HERUNTERFAHREN", "System wird sicher beendet")
    if state is SystemState.RESTARTING:
        return ("RESTARTING", "System is restarting") if english else ("NEUSTART", "System wird neu gestartet")
    if state is SystemState.SUSPENDING:
        return ("STANDBY", "Entering standby") if english else ("STANDBY", "Standby wird vorbereitet")
    if state is SystemState.TRANSITIONING:
        return ("TRANSITION", "Ending current session") if english else ("SYSTEMWECHSEL", "Aktuelle Sitzung wird beendet")
    if state is SystemState.IDLE:
        return ("IDLE", "Waiting for activity") if english else ("BEREIT", "Warten auf Aktivität")
    return title.upper(), detail or _fallback_state_detail(state, title)


def _draw_reference_side_frame(painter: QPainter, width: int, height: int, short: float, palette: _Theme) -> None:
    """Draw the independent cyan/magenta enclosure from the approved reference."""
    painter.save()
    for side, color_name in ((1, palette.cyan), (-1, palette.magenta)):
        color = QColor(color_name)
        color.setAlpha(225)
        x_outer = width * (0.055 if side > 0 else 0.945)
        x_inner = width * (0.095 if side > 0 else 0.905)
        direction = 1 if side > 0 else -1
        path = QPainterPath(QPointF(x_outer, 0))
        path.lineTo(QPointF(x_outer, height * 0.060))
        path.lineTo(QPointF(x_inner, height * 0.095))
        path.lineTo(QPointF(x_inner, height * 0.160))
        path.lineTo(QPointF(x_outer + direction * width * 0.018, height * 0.190))
        path.lineTo(QPointF(x_outer + direction * width * 0.018, height * 0.705))
        path.lineTo(QPointF(x_inner, height * 0.745))
        path.lineTo(QPointF(x_inner, height * 0.835))
        path.lineTo(QPointF(x_outer, height * 0.865))
        path.lineTo(QPointF(x_outer, height * 0.930))
        glow = QColor(color)
        glow.setAlpha(38)
        painter.setPen(QPen(glow, max(5.0, short * 0.020), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.setPen(QPen(color, max(1.2, short * 0.0040), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

        dot_x = width * (0.036 if side > 0 else 0.964)
        for base in (0.082, 0.778):
            for idx in range(5):
                dot = QColor(color_name)
                dot.setAlpha(185 - idx * 12)
                painter.setPen(Qt.NoPen)
                painter.setBrush(dot)
                painter.drawEllipse(QPointF(dot_x, height * base + idx * short * 0.030), short * 0.005, short * 0.005)
    painter.restore()


def _draw_reference_separator(painter: QPainter, width: int, y: float, short: float, palette: _Theme) -> None:
    gradient = QLinearGradient(width * 0.24, y, width * 0.76, y)
    gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
    gradient.setColorAt(0.38, QColor(palette.cyan))
    gradient.setColorAt(0.62, QColor(palette.magenta))
    gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.save()
    painter.setOpacity(0.18)
    painter.setPen(QPen(QBrush(gradient), max(7.0, short * 0.017), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.24, y), QPointF(width * 0.76, y))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(gradient), max(1.4, short * 0.003), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.24, y), QPointF(width * 0.76, y))
    painter.restore()


def _draw_reference_floor(painter: QPainter, width: int, height: int, short: float, palette: _Theme, horizon: float) -> None:
    """Reference-style luminous floor with a curved horizon and sparse perspective lines."""
    painter.save()
    path = QPainterPath(QPointF(width * 0.10, horizon + short * 0.020))
    path.quadTo(QPointF(width * 0.50, horizon - short * 0.020), QPointF(width * 0.90, horizon + short * 0.020))
    grad = QLinearGradient(width * 0.10, horizon, width * 0.90, horizon)
    grad.setColorAt(0.0, QColor(palette.cyan))
    grad.setColorAt(0.50, QColor(palette.green))
    grad.setColorAt(1.0, QColor(palette.magenta))
    painter.setPen(QPen(QBrush(grad), max(2.0, short * 0.005), Qt.SolidLine, Qt.RoundCap))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)
    for x_ratio, color_name in ((0.32, palette.cyan), (0.50, palette.green), (0.68, palette.magenta)):
        color = QColor(color_name)
        color.setAlpha(120)
        painter.setPen(QPen(color, max(1.0, short * 0.0022)))
        x = width * x_ratio
        painter.drawLine(QPointF(x, horizon), QPointF(x, height * 0.965))
    grid = QColor(palette.secondary)
    grid.setAlpha(32)
    painter.setPen(QPen(grid, max(1.0, short * 0.0013)))
    for ratio in (0.915, 0.940, 0.963, 0.982):
        painter.drawLine(QPointF(width * 0.02, height * ratio), QPointF(width * 0.98, height * ratio))
    painter.restore()
'''
assert anchor in text
text = text.replace(anchor, helpers + anchor, 1)

portrait_pattern = re.compile(r'    if portrait:\n.*?\n    else:\n', re.S)
portrait_block = '''    if portrait:
        layout = _portrait_layout(width, height)
        headline, state_detail = _portrait_state_copy(state, title, detail)

        _draw_reference_side_frame(painter, width, height, short, palette)
        _draw_portrait_brand_hud(
            painter, layout.hud_center, layout.hud_diameter, short, palette, state, phase
        )
        _draw_brand_icon(painter, icon, layout.brand_icon_rect, short, palette)
        _draw_gradient_wordmark(
            painter, image, layout.wordmark_rect, palette, layout.wordmark_font_px
        )

        _draw_reference_separator(painter, width, layout.separator_y, short, palette)
        _draw_state_icon(painter, layout.state_icon_rect, state, palette, short)
        accent = QColor(_STATE_ACCENTS[state])
        _draw_centered_single_line(
            painter, image, layout.status_rect, headline, layout.status_font_px,
            palette.primary, bold=False, glow=accent.name(), family="DejaVu Sans"
        )
        _draw_centered_single_line(
            painter, image, layout.detail_rect, state_detail, width * 0.040,
            palette.secondary, bold=False, family="DejaVu Sans"
        )
        _draw_state_rail(painter, layout.bar_rect, palette, state, phase)

        context_y = layout.context_top
        if clock_text:
            _draw_centered_single_line(
                painter, image, QRectF(width * 0.13, context_y, width * 0.74, height * 0.060),
                clock_text, width * 0.118, palette.primary, bold=False, glow=palette.cyan,
                family="DejaVu Sans Condensed"
            )
        if date_text:
            _draw_centered_single_line(
                painter, image, QRectF(width * 0.17, context_y + height * 0.062, width * 0.66, height * 0.028),
                date_text, width * 0.040, palette.secondary, family="DejaVu Sans"
            )

        _draw_reference_floor(painter, width, height, short, palette, layout.floor_horizon)
        footer = f"{APP_NAME} {__version__}"
        _draw_centered_single_line(
            painter, image, QRectF(width * 0.16, height * 0.905, width * 0.68, height * 0.024),
            footer, width * 0.025, palette.muted, family="DejaVu Sans"
        )
    else:
'''
text, count = portrait_pattern.subn(portrait_block, text, count=1)
assert count == 1, f'portrait replacement count={count}'

path.write_text(text)
