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
        top="#071824",
        middle="#020912",
        bottom="#01040a",
        primary="#f5fbff",
        secondary="#b9d6e8",
        muted="#668093",
        cyan="#00e5ff",
        green="#50f38a",
        magenta="#ff2aab",
        rail="#39d9ff",
    ),
    "bazzite-inspired": _Theme(
        top="#11142b",
        middle="#07091a",
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
    """Return a deliberately bold portrait composition.

    The 8.8-inch VSDISPLAY is extremely tall. Treating the short edge as the
    primary scale keeps the hero graphic and state title visually dominant
    instead of leaving them as small labels in a large empty canvas.
    """
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("portrait layout dimensions must be positive")

    center = QPointF(width * 0.50, height * 0.305)
    diameter = width * 0.94
    return _PortraitLayout(
        hud_center=center,
        hud_diameter=diameter,
        wordmark_rect=QRectF(width * 0.055, center.y() - height * 0.034, width * 0.89, height * 0.068),
        wordmark_font_px=width * 0.122,
        status_rect=QRectF(width * 0.055, height * 0.468, width * 0.89, height * 0.095),
        status_font_px=width * 0.102,
        detail_rect=QRectF(width * 0.09, height * 0.558, width * 0.82, height * 0.048),
        detail_font_px=width * 0.041,
        bar_rect=QRectF(width * 0.17, height * 0.623, width * 0.66, max(10.0, width * 0.026)),
        context_top=height * 0.665,
        telemetry_y=height * 0.765,
        floor_horizon=height * 0.835,
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


def _fit_font(image: QImage, text: str, rect: QRectF, px: float, *, bold: bool = False) -> QFont:
    font = QFont("DejaVu Sans")
    font.setBold(bold)
    font.setPixelSize(max(1, round(px)))
    while font.pixelSize() > 8:
        metrics = QFontMetricsF(font, image)
        bounds = metrics.boundingRect(rect, Qt.AlignCenter | Qt.TextWordWrap, text)
        if bounds.width() <= rect.width() and bounds.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _draw_centered(
    painter: QPainter,
    image: QImage,
    rect: QRectF,
    text: str,
    px: float,
    color: str,
    *,
    bold: bool = False,
    glow: str | None = None,
) -> None:
    if not text:
        return
    font = _fit_font(image, text, rect, px, bold=bold)
    painter.setFont(font)
    flags = Qt.AlignCenter | Qt.TextWordWrap
    if glow:
        glow_color = QColor(glow)
        offsets = (
            (-3, 0, 20), (3, 0, 20), (0, -3, 20), (0, 3, 20),
            (-2, -2, 28), (2, -2, 28), (-2, 2, 28), (2, 2, 28),
            (-1, 0, 58), (1, 0, 58), (0, -1, 58), (0, 1, 58),
        )
        for dx, dy, alpha in offsets:
            glow_color.setAlpha(alpha)
            painter.setPen(glow_color)
            painter.drawText(rect.translated(dx, dy), flags, text)
    painter.setPen(QColor(color))
    painter.drawText(rect, flags, text)


def _draw_gradient_wordmark(
    painter: QPainter,
    image: QImage,
    rect: QRectF,
    palette: _Theme,
    px: float,
) -> None:
    """Draw the OwnDash hero wordmark with a real stroked neon halo."""
    font = _fit_font(image, APP_NAME, rect, px, bold=True)
    metrics = QFontMetricsF(font, image)
    bounds = metrics.boundingRect(APP_NAME)
    baseline_x = rect.center().x() - bounds.width() / 2.0 - bounds.left()
    baseline_y = rect.center().y() + (metrics.ascent() - metrics.descent()) / 2.0

    path = QPainterPath()
    path.addText(QPointF(baseline_x, baseline_y), font, APP_NAME)

    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, QColor(palette.cyan))
    gradient.setColorAt(0.48, QColor(palette.green))
    gradient.setColorAt(1.0, QColor(palette.magenta))

    painter.save()
    painter.setBrush(Qt.NoBrush)
    for stroke_width, alpha in ((18.0, 18), (10.0, 34), (5.0, 72)):
        brush = QBrush(gradient)
        painter.setOpacity(alpha / 255.0)
        painter.setPen(QPen(brush, stroke_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
    painter.setOpacity(1.0)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawPath(path)
    painter.restore()


def _neon_color_for_angle(palette: _Theme, degrees: float) -> QColor:
    normalized = degrees % 360.0
    if 55.0 <= normalized < 155.0:
        return QColor(palette.green)
    if 155.0 <= normalized < 285.0:
        return QColor(palette.cyan)
    return QColor(palette.magenta)


def _draw_segmented_ring(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    *,
    segments: int,
    coverage: float,
    width_scale: float,
    phase_degrees: float,
    alpha: int,
) -> None:
    ring = QRectF(
        center.x() - diameter / 2,
        center.y() - diameter / 2,
        diameter,
        diameter,
    )
    step = 360.0 / float(segments)
    span = step * coverage
    for index in range(segments):
        start = index * step + phase_degrees
        color = _neon_color_for_angle(palette, start + span / 2)

        # Wide translucent passes create the soft halo missing from simple
        # vector arcs, then a crisp saturated core keeps the HUD sharp.
        glow = QColor(color)
        glow.setAlpha(max(8, int(alpha * 0.12)))
        painter.setPen(
            QPen(
                glow,
                max(2.0, short * width_scale * 3.8),
                Qt.SolidLine,
                Qt.RoundCap,
            )
        )
        painter.drawArc(ring, int(start * 16), int(span * 16))

        color.setAlpha(alpha)
        painter.setPen(
            QPen(
                color,
                max(1.2, short * width_scale),
                Qt.SolidLine,
                Qt.RoundCap,
            )
        )
        painter.drawArc(ring, int(start * 16), int(span * 16))


def _draw_orbit_nodes(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    phase: float,
) -> None:
    for index, angle_deg in enumerate((18.0, 72.0, 142.0, 218.0, 292.0, 338.0)):
        angle = math.radians(angle_deg + phase * (42.0 if index % 2 == 0 else -28.0))
        radius = diameter * (0.51 if index % 3 else 0.46)
        point = QPointF(
            center.x() + math.cos(angle) * radius,
            center.y() + math.sin(angle) * radius,
        )
        color = QColor((palette.cyan, palette.green, palette.magenta)[index % 3])
        glow = QColor(color)
        glow.setAlpha(42)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(point, short * 0.024, short * 0.024)
        color.setAlpha(235)
        painter.setBrush(color)
        painter.drawEllipse(point, short * 0.007, short * 0.007)


def _draw_hud_rings(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    state: SystemState,
    phase: float,
) -> None:
    animated = state in _ANIMATED_STATES
    phase = (phase % 1.0) if animated else 0.0

    # Broad tri-color ambient bloom behind the HUD.
    for dx, color_name in ((-0.20, palette.cyan), (0.0, palette.green), (0.20, palette.magenta)):
        glow_center = QPointF(center.x() + diameter * dx, center.y())
        glow = QRadialGradient(glow_center, diameter * 0.62)
        core = QColor(color_name)
        core.setAlpha(30)
        clear = QColor(color_name)
        clear.setAlpha(0)
        glow.setColorAt(0.0, core)
        glow.setColorAt(1.0, clear)
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(
            QRectF(
                glow_center.x() - diameter * 0.62,
                glow_center.y() - diameter * 0.62,
                diameter * 1.24,
                diameter * 1.24,
            )
        )
        painter.restore()

    faint = QColor(palette.secondary)
    faint.setAlpha(38)
    painter.setBrush(Qt.NoBrush)
    for scale in (1.00, 0.91, 0.80, 0.66):
        d = diameter * scale
        painter.setPen(QPen(faint, max(1.0, short * 0.0024)))
        painter.drawEllipse(
            QRectF(center.x() - d / 2, center.y() - d / 2, d, d)
        )

    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.99,
        short,
        palette,
        segments=14,
        coverage=0.58,
        width_scale=0.016,
        phase_degrees=phase * 360.0,
        alpha=248,
    )
    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.89,
        short,
        palette,
        segments=18,
        coverage=0.34,
        width_scale=0.0085,
        phase_degrees=22.0 - phase * 190.0,
        alpha=195,
    )
    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.77,
        short,
        palette,
        segments=26,
        coverage=0.20,
        width_scale=0.0052,
        phase_degrees=phase * 105.0,
        alpha=145,
    )

    # Radial spokes and small broken chords add the layered instrument-panel
    # feel visible in the reference instead of leaving three isolated circles.
    for index in range(12):
        angle = math.radians(index * 30.0 - 90.0)
        inner = diameter * (0.35 if index % 3 else 0.31)
        outer = diameter * (0.43 if index % 3 else 0.47)
        color = _neon_color_for_angle(palette, index * 30.0)
        color.setAlpha(55 if index % 3 else 110)
        painter.setPen(QPen(color, max(1.0, short * 0.0025), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(
            QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner),
            QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer),
        )

    tick_outer = diameter * 0.535
    tick_inner = diameter * 0.505
    highlighted = int(phase * 40.0) % 40 if animated else -1
    for index in range(40):
        angle = math.radians(index * 9.0 - 90.0)
        p1 = QPointF(
            center.x() + math.cos(angle) * tick_inner,
            center.y() + math.sin(angle) * tick_inner,
        )
        p2 = QPointF(
            center.x() + math.cos(angle) * tick_outer,
            center.y() + math.sin(angle) * tick_outer,
        )
        color = QColor(palette.green if index == highlighted else palette.secondary)
        color.setAlpha(235 if index == highlighted else 64)
        painter.setPen(
            QPen(
                color,
                max(1.0, short * (0.006 if index == highlighted else 0.0022)),
                Qt.SolidLine,
                Qt.RoundCap,
            )
        )
        painter.drawLine(p1, p2)

    _draw_orbit_nodes(painter, center, diameter, short, palette, phase if animated else 0.0)


def _draw_side_rails(painter: QPainter, width: int, height: int, short: float, palette: _Theme) -> None:
    """Full-height angled rails and indicator dots from the supplied reference."""
    left = QColor(palette.cyan)
    right = QColor(palette.magenta)
    left.setAlpha(205)
    right.setAlpha(205)
    line_width = max(1.0, short * 0.004)

    def rail(x: float, side: int, color: QColor) -> None:
        inward = side * short * 0.075
        y0 = height * 0.02
        y1 = height * 0.11
        y2 = height * 0.19
        y3 = height * 0.77
        y4 = height * 0.84
        painter.setPen(QPen(color, line_width, Qt.SolidLine, Qt.SquareCap))
        painter.drawLine(QPointF(x, y0), QPointF(x, y1))
        painter.drawLine(QPointF(x, y1), QPointF(x + inward, y2))
        painter.drawLine(QPointF(x + inward, y2), QPointF(x + inward, y3))
        painter.drawLine(QPointF(x + inward, y3), QPointF(x, y4))

        # Secondary rail adds the layered frame depth of the reference.
        ghost = QColor(color)
        ghost.setAlpha(54)
        offset = side * short * 0.030
        painter.setPen(QPen(ghost, max(1.0, line_width * 0.65)))
        painter.drawLine(QPointF(x + offset, y0 + short * 0.04), QPointF(x + offset, y1))
        painter.drawLine(QPointF(x + offset, y1), QPointF(x + inward + offset, y2))
        painter.drawLine(QPointF(x + inward + offset, y2), QPointF(x + inward + offset, y3))

    rail(short * 0.04, 1, left)
    rail(width - short * 0.04, -1, right)

    dot_y = height * 0.095
    for index in range(10):
        alpha = 90 + index * 13
        lc = QColor(palette.cyan)
        rc = QColor(palette.magenta)
        lc.setAlpha(min(230, alpha))
        rc.setAlpha(min(230, alpha))
        radius = max(1.2, short * 0.0045)
        y = dot_y + index * short * 0.038
        painter.setPen(Qt.NoPen)
        painter.setBrush(lc)
        painter.drawEllipse(QPointF(short * 0.075, y), radius, radius)
        painter.setBrush(rc)
        painter.drawEllipse(QPointF(width - short * 0.075, y), radius, radius)

    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(left, line_width))
    painter.drawLine(QPointF(short * 0.04, height * 0.90), QPointF(short * 0.04, height * 0.965))
    painter.drawLine(QPointF(short * 0.04, height * 0.90), QPointF(short * 0.095, height * 0.865))
    painter.setPen(QPen(right, line_width))
    painter.drawLine(QPointF(width - short * 0.04, height * 0.90), QPointF(width - short * 0.04, height * 0.965))
    painter.drawLine(QPointF(width - short * 0.04, height * 0.90), QPointF(width - short * 0.095, height * 0.865))


def _draw_background_depth(painter: QPainter, width: int, height: int, short: float, palette: _Theme) -> None:
    """Add subtle scanlines, horizon geometry and a central stage glow."""
    center_glow = QRadialGradient(QPointF(width * 0.50, height * 0.33), width * 0.78)
    core = QColor(palette.cyan)
    core.setAlpha(18)
    mid = QColor(palette.magenta)
    mid.setAlpha(7)
    clear = QColor(0, 0, 0, 0)
    center_glow.setColorAt(0.0, core)
    center_glow.setColorAt(0.62, mid)
    center_glow.setColorAt(1.0, clear)
    painter.setPen(Qt.NoPen)
    painter.setBrush(center_glow)
    painter.drawEllipse(QRectF(-width * 0.20, height * 0.05, width * 1.40, width * 1.40))

    scan = QColor(palette.secondary)
    scan.setAlpha(10)
    painter.setPen(QPen(scan, 1.0))
    step = max(48.0, short * 0.16)
    y = height * 0.08
    while y < height * 0.82:
        painter.drawLine(QPointF(width * 0.12, y), QPointF(width * 0.88, y))
        y += step

    # Short floating brackets around the hero keep the center visually framed
    # without bringing back the old rounded card.
    for ratio, color_name in ((0.18, palette.cyan), (0.82, palette.magenta)):
        color = QColor(color_name)
        color.setAlpha(72)
        x = width * ratio
        painter.setPen(QPen(color, max(1.0, short * 0.0025)))
        painter.drawLine(QPointF(x, height * 0.255), QPointF(x, height * 0.355))
        inward = short * 0.045 if ratio < 0.5 else -short * 0.045
        painter.drawLine(QPointF(x, height * 0.255), QPointF(x + inward, height * 0.245))
        painter.drawLine(QPointF(x, height * 0.355), QPointF(x + inward, height * 0.365))


def _draw_floor_reflection(
    painter: QPainter,
    width: int,
    height: int,
    short: float,
    palette: _Theme,
    *,
    horizon: float | None = None,
) -> None:
    horizon = float(height * 0.835 if horizon is None else horizon)
    horizon_gradient = QLinearGradient(width * 0.06, horizon, width * 0.94, horizon)
    horizon_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
    c1 = QColor(palette.cyan)
    c1.setAlpha(215)
    c2 = QColor(palette.green)
    c2.setAlpha(205)
    c3 = QColor(palette.magenta)
    c3.setAlpha(215)
    horizon_gradient.setColorAt(0.24, c1)
    horizon_gradient.setColorAt(0.50, c2)
    horizon_gradient.setColorAt(0.76, c3)
    horizon_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

    glow_line = QPen(QBrush(horizon_gradient), max(5.0, short * 0.018), Qt.SolidLine, Qt.RoundCap)
    painter.save()
    painter.setOpacity(0.18)
    painter.setPen(glow_line)
    painter.drawLine(QPointF(width * 0.06, horizon), QPointF(width * 0.94, horizon))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(horizon_gradient), max(1.2, short * 0.0045), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.06, horizon), QPointF(width * 0.94, horizon))
    painter.restore()

    floor_glow = QRadialGradient(QPointF(width * 0.50, horizon), width * 0.72)
    glow_cyan = QColor(palette.cyan)
    glow_cyan.setAlpha(70)
    glow_green = QColor(palette.green)
    glow_green.setAlpha(36)
    clear = QColor(palette.magenta)
    clear.setAlpha(0)
    floor_glow.setColorAt(0.0, glow_cyan)
    floor_glow.setColorAt(0.38, glow_green)
    floor_glow.setColorAt(1.0, clear)
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(floor_glow)
    painter.drawEllipse(
        QRectF(width * -0.02, horizon - short * 0.16, width * 1.04, short * 1.18)
    )
    painter.restore()

    reflections = (
        (0.27, palette.cyan, 0.58, 0.010),
        (0.38, palette.cyan, 0.36, 0.006),
        (0.49, palette.green, 0.82, 0.015),
        (0.61, palette.magenta, 0.43, 0.008),
        (0.72, palette.magenta, 0.60, 0.011),
    )
    for x_ratio, value, length, width_scale in reflections:
        color = QColor(value)
        color.setAlpha(128)
        fade = QLinearGradient(0, horizon, 0, min(height, horizon + short * length))
        fade.setColorAt(0.0, color)
        tail = QColor(value)
        tail.setAlpha(0)
        fade.setColorAt(1.0, tail)
        painter.setPen(QPen(QBrush(fade), max(2.0, short * width_scale), Qt.SolidLine, Qt.RoundCap))
        x = width * x_ratio
        painter.drawLine(QPointF(x, horizon), QPointF(x, min(height, horizon + short * length)))


def _draw_progress_bar(
    painter: QPainter,
    rect: QRectF,
    short: float,
    palette: _Theme,
    state: SystemState,
    phase: float,
) -> None:
    """Draw a slim luminous state rail, not a fake progress percentage."""
    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    cyan = QColor(palette.cyan)
    green = QColor(palette.green)
    magenta = QColor(palette.magenta)
    gradient.setColorAt(0.0, cyan)
    gradient.setColorAt(0.48, green)
    gradient.setColorAt(1.0, magenta)

    painter.save()
    painter.setOpacity(0.16)
    painter.setPen(QPen(QBrush(gradient), max(5.0, rect.height() * 1.45), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(rect.center().x() - rect.width() / 2, rect.center().y(), rect.center().x() + rect.width() / 2, rect.center().y())
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(gradient), max(1.5, rect.height() * 0.22), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(rect.center().x() - rect.width() / 2, rect.center().y(), rect.center().x() + rect.width() / 2, rect.center().y())

    # Bright scanner capsule. It only moves on states that are already allowed
    # to animate; terminal/suspend frames remain deterministic.
    scanner_ratio = 0.50
    if state in _ANIMATED_STATES:
        scanner_ratio = 0.12 + 0.76 * (0.5 + 0.5 * math.sin(phase * math.tau - math.pi / 2))
    elif state is SystemState.RESTARTING:
        scanner_ratio = 0.67
    elif state is SystemState.SHUTTING_DOWN:
        scanner_ratio = 0.82
    elif state is SystemState.SUSPENDING:
        scanner_ratio = 0.58
    scanner_x = rect.left() + rect.width() * scanner_ratio
    scanner = QColor(palette.primary)
    scanner.setAlpha(245)
    glow = QColor(_STATE_ACCENTS[state])
    glow.setAlpha(48)
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QPointF(scanner_x, rect.center().y()), rect.height() * 0.85, rect.height() * 0.85)
    painter.setBrush(scanner)
    painter.drawEllipse(QPointF(scanner_x, rect.center().y()), rect.height() * 0.20, rect.height() * 0.20)
    painter.restore()


def render_system_state_image(
    width: int,
    height: int,
    state: SystemState,
    theme: str,
    icon: QIcon,
    strings: dict[str, str],
    *,
    clock_text: str | None = None,
    date_text: str | None = None,
    sensor_text: str | None = None,
    animation_phase: float = 0.0,
) -> QImage:
    """Render one full-bleed OwnDash system-state frame.

    The supplied reference is used as a composition target: dark full-screen
    field, side rails, a large tri-color circular HUD, gradient OwnDash wordmark,
    a narrow status rail and floor-like neon reflections. No reference raster or
    third-party branding is embedded. ``animation_phase`` only changes IDLE and
    LOCKED geometry; terminal/suspend frames remain deterministic.
    """
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

    background = QLinearGradient(0, 0, width * 0.78, height)
    background.setColorAt(0.0, QColor(palette.top))
    background.setColorAt(0.48, QColor(palette.middle))
    background.setColorAt(1.0, QColor(palette.bottom))
    painter.fillRect(image.rect(), background)

    short = float(min(width, height))
    portrait = height >= width * 1.35
    title, detail = _state_text(state, strings)

    _draw_background_depth(painter, width, height, short, palette)
    _draw_side_rails(painter, width, height, short, palette)

    if portrait:
        layout = _portrait_layout(width, height)
        center = layout.hud_center
        diameter = layout.hud_diameter
        _draw_hud_rings(painter, center, diameter, short, palette, state, phase)

        if not icon.isNull():
            icon_side = max(20, int(width * 0.092))
            target = QRectF(
                center.x() - icon_side / 2,
                center.y() - diameter * 0.235,
                icon_side,
                icon_side,
            )
            painter.setOpacity(0.84)
            painter.drawPixmap(target.toRect(), icon.pixmap(icon_side, icon_side))
            painter.setOpacity(1.0)

        _draw_gradient_wordmark(
            painter,
            image,
            layout.wordmark_rect,
            palette,
            layout.wordmark_font_px,
        )

        # The status is intentionally much larger than v1. A white core with a
        # state-colored halo reads sharply from across a desk while retaining
        # the neon identity of the reference.
        _draw_centered(
            painter,
            image,
            layout.status_rect,
            title.upper(),
            layout.status_font_px,
            palette.primary,
            bold=True,
            glow=accent.name(),
        )
        if detail:
            _draw_centered(
                painter,
                image,
                layout.detail_rect,
                detail,
                layout.detail_font_px,
                palette.secondary,
                glow=accent.name(),
            )

        _draw_progress_bar(painter, layout.bar_rect, short, palette, state, phase)

        context_y = layout.context_top
        if clock_text:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.12, context_y, width * 0.76, height * 0.050),
                clock_text,
                width * 0.072,
                palette.primary,
                bold=True,
                glow=palette.cyan,
            )
            context_y += height * 0.052
        if date_text and state is SystemState.LOCKED:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.15, context_y, width * 0.70, height * 0.030),
                date_text,
                width * 0.031,
                palette.secondary,
            )
            context_y += height * 0.036
        if sensor_text and state in _ANIMATED_STATES:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.08, context_y, width * 0.84, height * 0.035),
                sensor_text,
                width * 0.028,
                palette.muted,
            )

        # Telemetry equalizer: denser and taller than v1, visually bridging the
        # status rail with the illuminated floor instead of leaving dead space.
        for index in range(25):
            x = width * 0.22 + index * width * 0.0235
            color = QColor(palette.cyan if index < 9 else palette.green if index < 16 else palette.magenta)
            color.setAlpha(68 + (index % 5) * 30)
            height_scale = 0.004 + 0.005 * (0.5 + 0.5 * math.sin(index * 1.35 + phase * math.tau))
            painter.setPen(QPen(color, max(1.0, short * 0.0032), Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(
                QPointF(x, layout.telemetry_y),
                QPointF(x, layout.telemetry_y + height * height_scale),
            )

        _draw_floor_reflection(
            painter,
            width,
            height,
            short,
            palette,
            horizon=layout.floor_horizon,
        )
        _draw_centered(
            painter,
            image,
            QRectF(width * 0.18, height * 0.932, width * 0.64, height * 0.026),
            f"{APP_NAME} · {__version__}",
            width * 0.022,
            palette.muted,
        )
    else:
        center = QPointF(width * 0.36, height * 0.48)
        diameter = min(height * 0.86, width * 0.44)
        _draw_hud_rings(painter, center, diameter, short, palette, state, phase)
        _draw_gradient_wordmark(
            painter,
            image,
            QRectF(width * 0.52, height * 0.20, width * 0.42, height * 0.18),
            palette,
            short * 0.145,
        )
        _draw_centered(
            painter,
            image,
            QRectF(width * 0.50, height * 0.39, width * 0.45, height * 0.18),
            title.upper(),
            short * 0.105,
            palette.primary,
            bold=True,
            glow=accent.name(),
        )
        if detail:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.54, height * 0.56, width * 0.38, height * 0.09),
                detail,
                short * 0.047,
                palette.secondary,
            )
        bar = QRectF(width * 0.58, height * 0.70, width * 0.29, max(9.0, short * 0.026))
        _draw_progress_bar(painter, bar, short, palette, state, phase)
        context = " · ".join(
            part for part in (
                clock_text or "",
                date_text if state is SystemState.LOCKED else "",
                sensor_text if state in _ANIMATED_STATES else "",
            ) if part
        )
        if context:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.50, height * 0.79, width * 0.45, height * 0.09),
                context,
                short * 0.040,
                palette.secondary,
            )

    painter.end()
    return image
