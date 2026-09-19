"""Resolution-independent neon HUD screens for Linux system states."""
from __future__ import annotations

from dataclasses import dataclass
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

from owndash import APP_NAME, __version__
from owndash.core.system_state import SystemState


@dataclass(frozen=True, slots=True)
class _Theme:
    top: str
    middle: str
    bottom: str
    primary: str
    secondary: str
    muted: str
    cyan: str
    green: str
    magenta: str
    rail: str


@dataclass(frozen=True, slots=True)
class _PortraitLayout:
    """Reference-scale geometry for the narrow 480×1920 class of displays."""

    hud_center: QPointF
    hud_diameter: float
    wordmark_rect: QRectF
    wordmark_font_px: float
    status_rect: QRectF
    status_font_px: float
    detail_rect: QRectF
    detail_font_px: float
    bar_rect: QRectF
    context_top: float
    telemetry_y: float
    floor_horizon: float


_THEMES = {
    "owndash": _Theme(
        top="#06141f",
        middle="#020811",
        bottom="#010307",
        primary="#f7fcff",
        secondary="#b8d5e6",
        muted="#61798a",
        cyan="#00e7ff",
        green="#5af59a",
        magenta="#ff2aae",
        rail="#37dcff",
    ),
    "bazzite-inspired": _Theme(
        top="#10142a",
        middle="#070919",
        bottom="#02040d",
        primary="#f8f6ff",
        secondary="#cbc8ff",
        muted="#8581a8",
        cyan="#55d9ff",
        green="#8d7cff",
        magenta="#d95cff",
        rail="#6f8dff",
    ),
}

_STATE_ACCENTS = {
    SystemState.IDLE: "#50f38a",
    SystemState.LOCKED: "#00e5ff",
    SystemState.SUSPENDING: "#63d8ff",
    SystemState.SHUTTING_DOWN: "#ff9c62",
    SystemState.RESTARTING: "#cf7cff",
}

_STATE_KEYS = {
    SystemState.IDLE: ("idle", ""),
    SystemState.LOCKED: ("system_locked", ""),
    SystemState.SUSPENDING: ("standby", "entering_standby"),
    SystemState.SHUTTING_DOWN: ("shutting_down", ""),
    SystemState.RESTARTING: ("restarting", ""),
}

_ANIMATED_STATES = {SystemState.IDLE, SystemState.LOCKED}


def _portrait_layout(width: int, height: int) -> _PortraitLayout:
    """Return the bold v3 portrait composition used by tall USB panels."""
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("portrait layout dimensions must be positive")

    center = QPointF(width * 0.50, height * 0.292)
    diameter = width * 0.96
    return _PortraitLayout(
        hud_center=center,
        hud_diameter=diameter,
        wordmark_rect=QRectF(width * 0.025, center.y() - height * 0.041, width * 0.95, height * 0.082),
        wordmark_font_px=width * 0.18,
        status_rect=QRectF(width * 0.025, height * 0.455, width * 0.95, height * 0.070),
        status_font_px=width * 0.095,
        detail_rect=QRectF(width * 0.08, height * 0.523, width * 0.84, height * 0.043),
        detail_font_px=width * 0.038,
        bar_rect=QRectF(width * 0.18, height * 0.585, width * 0.64, max(10.0, width * 0.024)),
        context_top=height * 0.625,
        telemetry_y=height * 0.735,
        floor_horizon=height * 0.815,
    )


def _point_on_circle(center: QPointF, radius: float, degrees: float) -> QPointF:
    angle = math.radians(degrees)
    return QPointF(center.x() + math.cos(angle) * radius, center.y() + math.sin(angle) * radius)


def _portrait_rail_docks(layout: _PortraitLayout) -> tuple[QPointF, QPointF, QPointF, QPointF]:
    """Return rail-to-HUD junctions in visual order."""
    radius = layout.hud_diameter / 2.0
    return (
        _point_on_circle(layout.hud_center, radius, 215.0),
        _point_on_circle(layout.hud_center, radius, 145.0),
        _point_on_circle(layout.hud_center, radius, 325.0),
        _point_on_circle(layout.hud_center, radius, 35.0),
    )


def _text(strings: dict[str, str], key: str, fallback: str) -> str:
    value = strings.get(key)
    return str(value) if value else fallback


def _state_text(state: SystemState, strings: dict[str, str]) -> tuple[str, str]:
    defaults = {
        "idle": "Idle",
        "system_locked": "System locked",
        "standby": "Standby",
        "entering_standby": "Entering standby",
        "shutting_down": "Shutting down",
        "restarting": "Restarting",
    }
    title_key, detail_key = _STATE_KEYS[state]
    title = _text(strings, title_key, defaults[title_key])
    detail = _text(strings, detail_key, defaults[detail_key]) if detail_key else ""
    return title, detail


def _fit_font(image: QImage, text: str, rect: QRectF, px: float, *, bold: bool = False, family: str = "DejaVu Sans") -> QFont:
    font = QFont(family)
    font.setBold(bold)
    font.setPixelSize(max(1, round(px)))
    while font.pixelSize() > 8:
        metrics = QFontMetricsF(font, image)
        bounds = metrics.boundingRect(rect, Qt.AlignCenter | Qt.TextWordWrap, text)
        if bounds.width() <= rect.width() and bounds.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _draw_centered(painter: QPainter, image: QImage, rect: QRectF, text: str, px: float, color: str, *, bold: bool = False, glow: str | None = None, family: str = "DejaVu Sans") -> None:
    if not text:
        return
    font = _fit_font(image, text, rect, px, bold=bold, family=family)
    painter.setFont(font)
    flags = Qt.AlignCenter | Qt.TextWordWrap
    if glow:
        glow_color = QColor(glow)
        for dx, dy, alpha in ((-4, 0, 14), (4, 0, 14), (0, -4, 14), (0, 4, 14), (-2, -2, 28), (2, -2, 28), (-2, 2, 28), (2, 2, 28), (-1, 0, 70), (1, 0, 70), (0, -1, 70), (0, 1, 70)):
            glow_color.setAlpha(alpha)
            painter.setPen(glow_color)
            painter.drawText(rect.translated(dx, dy), flags, text)
    painter.setPen(QColor(color))
    painter.drawText(rect, flags, text)


def _draw_gradient_wordmark(painter: QPainter, image: QImage, rect: QRectF, palette: _Theme, px: float) -> None:
    """Draw the large central OwnDash hero mark with layered neon glow."""
    font = _fit_font(image, APP_NAME, rect, px, bold=True)
    metrics = QFontMetricsF(font, image)
    bounds = metrics.boundingRect(APP_NAME)
    baseline_x = rect.center().x() - bounds.width() / 2.0 - bounds.left()
    baseline_y = rect.center().y() + (metrics.ascent() - metrics.descent()) / 2.0
    path = QPainterPath()
    path.addText(QPointF(baseline_x, baseline_y), font, APP_NAME)
    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, QColor(palette.cyan))
    gradient.setColorAt(0.46, QColor(palette.green))
    gradient.setColorAt(1.0, QColor(palette.magenta))
    painter.save()
    painter.setBrush(Qt.NoBrush)
    for stroke_width, opacity in ((26.0, 0.055), (16.0, 0.10), (9.0, 0.17), (4.0, 0.38)):
        painter.setOpacity(opacity)
        painter.setPen(QPen(QBrush(gradient), stroke_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
    painter.setOpacity(1.0)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawPath(path)
    painter.setOpacity(0.22)
    painter.setPen(QPen(QColor("#ffffff"), 0.8))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)
    painter.restore()


def _neon_color_for_angle(palette: _Theme, degrees: float) -> QColor:
    normalized = degrees % 360.0
    if 55.0 <= normalized < 135.0:
        return QColor(palette.green)
    if 135.0 <= normalized < 270.0:
        return QColor(palette.cyan)
    return QColor(palette.magenta)


def _draw_segmented_ring(painter: QPainter, center: QPointF, diameter: float, short: float, palette: _Theme, *, segments: int, coverage: float, width_scale: float, phase_degrees: float, alpha: int) -> None:
    ring = QRectF(center.x() - diameter / 2.0, center.y() - diameter / 2.0, diameter, diameter)
    step = 360.0 / float(segments)
    span = step * coverage
    for index in range(segments):
        start = index * step + phase_degrees
        color = _neon_color_for_angle(palette, start + span / 2.0)
        halo = QColor(color)
        halo.setAlpha(max(8, int(alpha * 0.12)))
        painter.setPen(QPen(halo, max(3.0, short * width_scale * 4.2), Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, int(start * 16), int(span * 16))
        color.setAlpha(alpha)
        painter.setPen(QPen(color, max(1.2, short * width_scale), Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, int(start * 16), int(span * 16))


def _draw_hud_rings(painter: QPainter, center: QPointF, diameter: float, short: float, palette: _Theme, state: SystemState, phase: float) -> None:
    animated = state in _ANIMATED_STATES
    phase = (phase % 1.0) if animated else 0.0
    for dx, color_name in ((-0.23, palette.cyan), (0.0, palette.green), (0.23, palette.magenta)):
        glow_center = QPointF(center.x() + diameter * dx, center.y())
        glow = QRadialGradient(glow_center, diameter * 0.58)
        core = QColor(color_name)
        core.setAlpha(28)
        clear = QColor(color_name)
        clear.setAlpha(0)
        glow.setColorAt(0.0, core)
        glow.setColorAt(1.0, clear)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(glow_center.x() - diameter * 0.58, glow_center.y() - diameter * 0.58, diameter * 1.16, diameter * 1.16))
    structural = QColor(palette.secondary)
    structural.setAlpha(44)
    painter.setBrush(Qt.NoBrush)
    for scale in (1.00, 0.82, 0.66):
        d = diameter * scale
        painter.setPen(QPen(structural, max(1.0, short * 0.0024)))
        painter.drawEllipse(QRectF(center.x() - d / 2, center.y() - d / 2, d, d))
    _draw_segmented_ring(painter, center, diameter * 0.985, short, palette, segments=10, coverage=0.60, width_scale=0.017, phase_degrees=phase * 190.0, alpha=250)
    _draw_segmented_ring(painter, center, diameter * 0.84, short, palette, segments=14, coverage=0.28, width_scale=0.0075, phase_degrees=16.0 - phase * 115.0, alpha=175)
    _draw_segmented_ring(painter, center, diameter * 0.69, short, palette, segments=18, coverage=0.15, width_scale=0.0042, phase_degrees=phase * 65.0, alpha=112)
    for index in range(8):
        degrees = index * 45.0 - 90.0
        angle = math.radians(degrees)
        inner = diameter * 0.33
        outer = diameter * (0.43 if index % 2 else 0.47)
        color = _neon_color_for_angle(palette, degrees)
        color.setAlpha(58 if index % 2 else 100)
        painter.setPen(QPen(color, max(1.0, short * 0.0022), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner), QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer))
    highlighted = int(phase * 32.0) % 32 if animated else -1
    for index in range(32):
        angle = math.radians(index * 11.25 - 90.0)
        inner = diameter * 0.505
        outer = diameter * 0.527
        p1 = QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner)
        p2 = QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer)
        color = QColor(palette.green if index == highlighted else palette.secondary)
        color.setAlpha(230 if index == highlighted else 52)
        painter.setPen(QPen(color, max(1.0, short * (0.005 if index == highlighted else 0.0018)), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(p1, p2)
    for index, base in enumerate((28.0, 118.0, 208.0, 298.0)):
        degrees = base + (phase * 24.0 if animated else 0.0)
        point = _point_on_circle(center, diameter * 0.455, degrees)
        color = QColor((palette.magenta, palette.green, palette.cyan, palette.magenta)[index])
        glow = QColor(color)
        glow.setAlpha(45)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(point, short * 0.020, short * 0.020)
        color.setAlpha(235)
        painter.setBrush(color)
        painter.drawEllipse(point, short * 0.0065, short * 0.0065)


def _draw_dock_node(painter: QPainter, point: QPointF, color: QColor, short: float) -> None:
    halo = QColor(color)
    halo.setAlpha(42)
    painter.setPen(Qt.NoPen)
    painter.setBrush(halo)
    painter.drawEllipse(point, short * 0.030, short * 0.030)
    color.setAlpha(245)
    painter.setBrush(color)
    painter.drawEllipse(point, short * 0.007, short * 0.007)


def _draw_side_rails(painter: QPainter, width: int, height: int, short: float, palette: _Theme, *, layout: _PortraitLayout | None = None) -> None:
    left = QColor(palette.cyan)
    right = QColor(palette.magenta)
    left.setAlpha(210)
    right.setAlpha(210)
    line_width = max(1.0, short * 0.004)
    if layout is None:
        for x, side, color in ((short * 0.04, 1, left), (width - short * 0.04, -1, right)):
            inward = side * short * 0.075
            painter.setPen(QPen(color, line_width, Qt.SolidLine, Qt.SquareCap))
            painter.drawLine(QPointF(x, height * 0.03), QPointF(x, height * 0.13))
            painter.drawLine(QPointF(x, height * 0.13), QPointF(x + inward, height * 0.22))
            painter.drawLine(QPointF(x + inward, height * 0.22), QPointF(x + inward, height * 0.80))
        return
    upper_left, lower_left, upper_right, lower_right = _portrait_rail_docks(layout)
    def draw_one(color: QColor, *, side: int, upper: QPointF, lower: QPointF) -> None:
        outer_x = width * (0.055 if side > 0 else 0.945)
        track_x = width * (0.115 if side > 0 else 0.885)
        top_y = height * 0.025
        shoulder_y = height * 0.115
        lower_shoulder_y = height * 0.735
        bottom_y = height * 0.905
        path = QPainterPath(QPointF(outer_x, top_y))
        path.lineTo(QPointF(outer_x, shoulder_y))
        path.lineTo(QPointF(track_x, shoulder_y + height * 0.055))
        path.lineTo(QPointF(track_x, upper.y() - short * 0.035))
        path.lineTo(upper)
        lower_path = QPainterPath(lower)
        lower_path.lineTo(QPointF(track_x, lower.y() + short * 0.035))
        lower_path.lineTo(QPointF(track_x, lower_shoulder_y))
        lower_path.lineTo(QPointF(outer_x, lower_shoulder_y + height * 0.055))
        lower_path.lineTo(QPointF(outer_x, bottom_y))
        glow = QColor(color)
        glow.setAlpha(42)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(glow, line_width * 4.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        painter.drawPath(lower_path)
        painter.setPen(QPen(color, line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        painter.drawPath(lower_path)
        inner = QColor(color)
        inner.setAlpha(58)
        offset = side * short * 0.030
        painter.setPen(QPen(inner, max(1.0, line_width * 0.62), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(outer_x + offset, top_y + short * 0.05), QPointF(outer_x + offset, shoulder_y))
        painter.drawLine(QPointF(track_x + offset, shoulder_y + height * 0.060), QPointF(track_x + offset, upper.y() - short * 0.055))
        painter.drawLine(QPointF(track_x + offset, lower.y() + short * 0.055), QPointF(track_x + offset, lower_shoulder_y - short * 0.02))
        _draw_dock_node(painter, upper, QColor(color), short)
        _draw_dock_node(painter, lower, QColor(color), short)
    draw_one(left, side=1, upper=upper_left, lower=lower_left)
    draw_one(right, side=-1, upper=upper_right, lower=lower_right)
    for index in range(7):
        y = height * 0.100 + index * short * 0.037
        radius = max(1.2, short * 0.0042)
        for x, color_name in ((width * 0.083, palette.cyan), (width * 0.917, palette.magenta)):
            color = QColor(color_name)
            color.setAlpha(105 + index * 18)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), radius, radius)


def _draw_background_depth(painter: QPainter, width: int, height: int, short: float, palette: _Theme) -> None:
    center_glow = QRadialGradient(QPointF(width * 0.50, height * 0.30), width * 0.78)
    core = QColor(palette.cyan)
    core.setAlpha(17)
    mid = QColor(palette.magenta)
    mid.setAlpha(7)
    clear = QColor(0, 0, 0, 0)
    center_glow.setColorAt(0.0, core)
    center_glow.setColorAt(0.62, mid)
    center_glow.setColorAt(1.0, clear)
    painter.setPen(Qt.NoPen)
    painter.setBrush(center_glow)
    painter.drawEllipse(QRectF(-width * 0.20, height * 0.045, width * 1.40, width * 1.40))
    scan = QColor(palette.secondary)
    scan.setAlpha(7)
    painter.setPen(QPen(scan, 1.0))
    step = max(82.0, short * 0.23)
    y = height * 0.09
    while y < height * 0.76:
        painter.drawLine(QPointF(width * 0.15, y), QPointF(width * 0.85, y))
        y += step


def _draw_floor_reflection(painter: QPainter, width: int, height: int, short: float, palette: _Theme, *, horizon: float | None = None) -> None:
    horizon = float(height * 0.815 if horizon is None else horizon)
    line_gradient = QLinearGradient(width * 0.06, horizon, width * 0.94, horizon)
    line_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
    cyan = QColor(palette.cyan)
    green = QColor(palette.green)
    magenta = QColor(palette.magenta)
    cyan.setAlpha(220)
    green.setAlpha(205)
    magenta.setAlpha(220)
    line_gradient.setColorAt(0.24, cyan)
    line_gradient.setColorAt(0.50, green)
    line_gradient.setColorAt(0.76, magenta)
    line_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.save()
    painter.setOpacity(0.16)
    painter.setPen(QPen(QBrush(line_gradient), max(7.0, short * 0.022), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.07, horizon), QPointF(width * 0.93, horizon))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(line_gradient), max(1.2, short * 0.004), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.07, horizon), QPointF(width * 0.93, horizon))
    wash = QLinearGradient(0, horizon, 0, height)
    wash_top = QColor(palette.cyan)
    wash_mid = QColor(palette.green)
    wash_tail = QColor(palette.magenta)
    wash_top.setAlpha(34)
    wash_mid.setAlpha(16)
    wash_tail.setAlpha(0)
    wash.setColorAt(0.0, wash_top)
    wash.setColorAt(0.34, wash_mid)
    wash.setColorAt(1.0, wash_tail)
    painter.setPen(Qt.NoPen)
    painter.setBrush(wash)
    painter.drawRect(QRectF(width * 0.08, horizon, width * 0.84, height - horizon))
    grid = QColor(palette.secondary)
    grid.setAlpha(18)
    painter.setPen(QPen(grid, max(1.0, short * 0.0016)))
    for ratio in (0.24, 0.36, 0.50, 0.64, 0.76):
        x0 = width * ratio
        x1 = width * (0.50 + (ratio - 0.50) * 1.8)
        painter.drawLine(QPointF(x0, horizon), QPointF(x1, height * 0.965))
    for y_ratio in (0.845, 0.875, 0.910, 0.950):
        painter.drawLine(QPointF(width * 0.16, height * y_ratio), QPointF(width * 0.84, height * y_ratio))
    reflections = ((0.30, palette.cyan, 0.62, 0.011), (0.43, palette.cyan, 0.42, 0.006), (0.50, palette.green, 0.80, 0.014), (0.60, palette.magenta, 0.46, 0.007), (0.71, palette.magenta, 0.64, 0.011))
    for x_ratio, value, length, width_scale in reflections:
        color = QColor(value)
        color.setAlpha(135)
        fade = QLinearGradient(0, horizon, 0, min(height, horizon + short * length))
        fade.setColorAt(0.0, color)
        tail = QColor(value)
        tail.setAlpha(0)
        fade.setColorAt(1.0, tail)
        painter.setPen(QPen(QBrush(fade), max(2.0, short * width_scale), Qt.SolidLine, Qt.RoundCap))
        x = width * x_ratio
        painter.drawLine(QPointF(x, horizon), QPointF(x, min(height, horizon + short * length)))
    painter.restore()


def _draw_state_rail(painter: QPainter, rect: QRectF, palette: _Theme, state: SystemState, phase: float) -> None:
    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, QColor(palette.cyan))
    gradient.setColorAt(0.48, QColor(palette.green))
    gradient.setColorAt(1.0, QColor(palette.magenta))
    painter.save()
    painter.setOpacity(0.13)
    painter.setPen(QPen(QBrush(gradient), max(6.0, rect.height() * 1.55), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(rect.left(), rect.center().y()), QPointF(rect.right(), rect.center().y()))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(gradient), max(1.4, rect.height() * 0.20), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(rect.left(), rect.center().y()), QPointF(rect.right(), rect.center().y()))
    scanner_ratio = 0.50
    if state in _ANIMATED_STATES:
        scanner_ratio = 0.14 + 0.72 * (0.5 + 0.5 * math.sin(phase * math.tau - math.pi / 2))
    elif state is SystemState.RESTARTING:
        scanner_ratio = 0.68
    elif state is SystemState.SHUTTING_DOWN:
        scanner_ratio = 0.82
    elif state is SystemState.SUSPENDING:
        scanner_ratio = 0.58
    scanner_x = rect.left() + rect.width() * scanner_ratio
    glow = QColor(_STATE_ACCENTS[state])
    glow.setAlpha(52)
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QPointF(scanner_x, rect.center().y()), rect.height() * 0.80, rect.height() * 0.80)
    painter.setBrush(QColor(palette.primary))
    painter.drawEllipse(QPointF(scanner_x, rect.center().y()), rect.height() * 0.18, rect.height() * 0.18)
    painter.restore()


def render_system_state_image(width: int, height: int, state: SystemState, theme: str, icon: QIcon, strings: dict[str, str], *, clock_text: str | None = None, date_text: str | None = None, sensor_text: str | None = None, animation_phase: float = 0.0) -> QImage:
    """Render one full-bleed OwnDash system-state frame."""
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")
    if state is SystemState.ACTIVE:
        raise ValueError("ACTIVE has no temporary system-state frame")
    if state not in _STATE_KEYS:
        raise ValueError(f"unsupported system state: {state}")
    palette = _THEMES.get(str(theme), _THEMES["owndash"])
    accent = QColor(_STATE_ACCENTS[state])
    phase = float(animation_phase % 1.0) if state in _ANIMATED_STATES else 0.0
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(palette.bottom))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    background = QLinearGradient(0, 0, width * 0.72, height)
    background.setColorAt(0.0, QColor(palette.top))
    background.setColorAt(0.46, QColor(palette.middle))
    background.setColorAt(1.0, QColor(palette.bottom))
    painter.fillRect(image.rect(), background)
    short = float(min(width, height))
    portrait = height >= width * 1.35
    title, detail = _state_text(state, strings)
    _draw_background_depth(painter, width, height, short, palette)
    if portrait:
        layout = _portrait_layout(width, height)
        _draw_side_rails(painter, width, height, short, palette, layout=layout)
        _draw_hud_rings(painter, layout.hud_center, layout.hud_diameter, short, palette, state, phase)
        _draw_gradient_wordmark(painter, image, layout.wordmark_rect, palette, layout.wordmark_font_px)
        _draw_centered(painter, image, QRectF(width * 0.18, layout.hud_center.y() + height * 0.032, width * 0.64, height * 0.026), "PC DASHBOARD SYSTEM", width * 0.026, palette.secondary, family="DejaVu Sans Condensed")
        _draw_centered(painter, image, layout.status_rect, title.upper(), layout.status_font_px, palette.primary, bold=True, glow=accent.name(), family="DejaVu Sans Condensed")
        if detail:
            _draw_centered(painter, image, layout.detail_rect, detail, layout.detail_font_px, palette.secondary, glow=accent.name(), family="DejaVu Sans Condensed")
        _draw_state_rail(painter, layout.bar_rect, palette, state, phase)
        context_y = layout.context_top
        if clock_text:
            _draw_centered(painter, image, QRectF(width * 0.12, context_y, width * 0.76, height * 0.050), clock_text, width * 0.071, palette.primary, bold=True, glow=palette.cyan)
            context_y += height * 0.051
        if date_text and state is SystemState.LOCKED:
            _draw_centered(painter, image, QRectF(width * 0.15, context_y, width * 0.70, height * 0.028), date_text, width * 0.030, palette.secondary)
            context_y += height * 0.034
        if sensor_text and state in _ANIMATED_STATES:
            _draw_centered(painter, image, QRectF(width * 0.08, context_y, width * 0.84, height * 0.032), sensor_text, width * 0.027, palette.muted)
        for index in range(17):
            x = width * 0.30 + index * width * 0.025
            color = QColor(palette.cyan if index < 6 else palette.green if index < 11 else palette.magenta)
            color.setAlpha(58 + (index % 4) * 24)
            length = height * (0.003 + 0.003 * (0.5 + 0.5 * math.sin(index * 1.2 + phase * math.tau)))
            painter.setPen(QPen(color, max(1.0, short * 0.0026), Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(x, layout.telemetry_y), QPointF(x, layout.telemetry_y + length))
        _draw_floor_reflection(painter, width, height, short, palette, horizon=layout.floor_horizon)
        _draw_centered(painter, image, QRectF(width * 0.18, height * 0.944, width * 0.64, height * 0.022), f"{APP_NAME} · {__version__}", width * 0.020, palette.muted)
    else:
        _draw_side_rails(painter, width, height, short, palette)
        center = QPointF(width * 0.36, height * 0.48)
        diameter = min(height * 0.86, width * 0.44)
        _draw_hud_rings(painter, center, diameter, short, palette, state, phase)
        _draw_gradient_wordmark(painter, image, QRectF(width * 0.51, height * 0.19, width * 0.44, height * 0.19), palette, short * 0.16)
        _draw_centered(painter, image, QRectF(width * 0.49, height * 0.40, width * 0.46, height * 0.17), title.upper(), short * 0.105, palette.primary, bold=True, glow=accent.name(), family="DejaVu Sans Condensed")
        if detail:
            _draw_centered(painter, image, QRectF(width * 0.53, height * 0.56, width * 0.39, height * 0.09), detail, short * 0.047, palette.secondary)
        bar = QRectF(width * 0.58, height * 0.70, width * 0.29, max(9.0, short * 0.026))
        _draw_state_rail(painter, bar, palette, state, phase)
        context = " · ".join(part for part in (clock_text or "", date_text if state is SystemState.LOCKED else "", sensor_text if state in _ANIMATED_STATES else "") if part)
        if context:
            _draw_centered(painter, image, QRectF(width * 0.50, height * 0.79, width * 0.45, height * 0.09), context, short * 0.040, palette.secondary)
    painter.end()
    return image
