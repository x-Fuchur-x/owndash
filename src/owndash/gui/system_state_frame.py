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
) -> None:
    if not text:
        return
    painter.setFont(_fit_font(image, text, rect, px, bold=bold))
    painter.setPen(QColor(color))
    painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, text)


def _draw_gradient_wordmark(
    painter: QPainter,
    image: QImage,
    rect: QRectF,
    palette: _Theme,
    px: float,
) -> None:
    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, QColor(palette.cyan))
    gradient.setColorAt(0.48, QColor(palette.green))
    gradient.setColorAt(1.0, QColor(palette.magenta))
    painter.setFont(_fit_font(image, APP_NAME, rect, px, bold=True))
    painter.setPen(QPen(QBrush(gradient), 1.0))
    painter.drawText(rect, Qt.AlignCenter, APP_NAME)


def _neon_color_for_angle(palette: _Theme, degrees: float) -> QColor:
    normalized = degrees % 360.0
    # Left side cyan, upper arc green, right/lower-right magenta: the same
    # visual rhythm as the supplied OwnDash reference without embedding it as
    # a raster asset.
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

    glow = QRadialGradient(center, diameter * 0.68)
    glow0 = QColor(palette.cyan)
    glow0.setAlpha(30)
    glow1 = QColor(palette.green)
    glow1.setAlpha(10)
    clear = QColor(palette.magenta)
    clear.setAlpha(0)
    glow.setColorAt(0.0, glow0)
    glow.setColorAt(0.52, glow1)
    glow.setColorAt(1.0, clear)
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(
        QRectF(
            center.x() - diameter * 0.64,
            center.y() - diameter * 0.64,
            diameter * 1.28,
            diameter * 1.28,
        )
    )
    painter.restore()

    faint = QColor(palette.secondary)
    faint.setAlpha(38)
    painter.setBrush(Qt.NoBrush)
    for scale in (1.00, 0.88, 0.73):
        d = diameter * scale
        painter.setPen(QPen(faint, max(1.0, short * 0.0024)))
        painter.drawEllipse(
            QRectF(center.x() - d / 2, center.y() - d / 2, d, d)
        )

    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.98,
        short,
        palette,
        segments=12,
        coverage=0.54,
        width_scale=0.014,
        phase_degrees=phase * 360.0,
        alpha=238,
    )
    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.85,
        short,
        palette,
        segments=16,
        coverage=0.30,
        width_scale=0.007,
        phase_degrees=18.0 - phase * 190.0,
        alpha=175,
    )
    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.70,
        short,
        palette,
        segments=24,
        coverage=0.18,
        width_scale=0.0045,
        phase_degrees=phase * 105.0,
        alpha=130,
    )

    tick_outer = diameter * 0.535
    tick_inner = diameter * 0.505
    highlighted = int(phase * 32.0) % 32 if animated else -1
    for index in range(32):
        angle = math.radians(index * 11.25 - 90.0)
        p1 = QPointF(
            center.x() + math.cos(angle) * tick_inner,
            center.y() + math.sin(angle) * tick_inner,
        )
        p2 = QPointF(
            center.x() + math.cos(angle) * tick_outer,
            center.y() + math.sin(angle) * tick_outer,
        )
        color = QColor(palette.green if index == highlighted else palette.secondary)
        color.setAlpha(230 if index == highlighted else 64)
        painter.setPen(
            QPen(
                color,
                max(1.0, short * (0.006 if index == highlighted else 0.0024)),
                Qt.SolidLine,
                Qt.RoundCap,
            )
        )
        painter.drawLine(p1, p2)


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

    rail(short * 0.04, 1, left)
    rail(width - short * 0.04, -1, right)

    dot_y = height * 0.095
    for index in range(8):
        alpha = 110 + index * 14
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

    # Bottom brackets repeat the upper technical language without boxing the
    # whole screen inside a card.
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(left, line_width))
    painter.drawLine(QPointF(short * 0.04, height * 0.90), QPointF(short * 0.04, height * 0.965))
    painter.drawLine(QPointF(short * 0.04, height * 0.90), QPointF(short * 0.095, height * 0.865))
    painter.setPen(QPen(right, line_width))
    painter.drawLine(QPointF(width - short * 0.04, height * 0.90), QPointF(width - short * 0.04, height * 0.965))
    painter.drawLine(QPointF(width - short * 0.04, height * 0.90), QPointF(width - short * 0.095, height * 0.865))


def _draw_floor_reflection(painter: QPainter, width: int, height: int, short: float, palette: _Theme) -> None:
    horizon = height * 0.835
    horizon_gradient = QLinearGradient(width * 0.10, horizon, width * 0.90, horizon)
    horizon_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
    c1 = QColor(palette.cyan)
    c1.setAlpha(180)
    c2 = QColor(palette.green)
    c2.setAlpha(180)
    c3 = QColor(palette.magenta)
    c3.setAlpha(180)
    horizon_gradient.setColorAt(0.28, c1)
    horizon_gradient.setColorAt(0.50, c2)
    horizon_gradient.setColorAt(0.72, c3)
    horizon_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(QPen(QBrush(horizon_gradient), max(1.0, short * 0.004)))
    painter.drawLine(QPointF(width * 0.10, horizon), QPointF(width * 0.90, horizon))

    floor_glow = QRadialGradient(QPointF(width * 0.50, horizon), width * 0.62)
    glow_cyan = QColor(palette.cyan)
    glow_cyan.setAlpha(54)
    glow_green = QColor(palette.green)
    glow_green.setAlpha(28)
    clear = QColor(palette.magenta)
    clear.setAlpha(0)
    floor_glow.setColorAt(0.0, glow_cyan)
    floor_glow.setColorAt(0.36, glow_green)
    floor_glow.setColorAt(1.0, clear)
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(floor_glow)
    painter.drawEllipse(
        QRectF(width * 0.05, horizon - short * 0.12, width * 0.90, short * 1.02)
    )
    painter.restore()

    reflections = (
        (0.34, palette.cyan, 0.52),
        (0.49, palette.green, 0.74),
        (0.66, palette.magenta, 0.50),
    )
    for x_ratio, value, length in reflections:
        color = QColor(value)
        color.setAlpha(110)
        fade = QLinearGradient(0, horizon, 0, min(height, horizon + short * length))
        fade.setColorAt(0.0, color)
        tail = QColor(value)
        tail.setAlpha(0)
        fade.setColorAt(1.0, tail)
        painter.setPen(QPen(QBrush(fade), max(2.0, short * 0.012), Qt.SolidLine, Qt.RoundCap))
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
    outline = QColor(palette.secondary)
    outline.setAlpha(165)
    radius = rect.height() / 2
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(outline, max(1.0, short * 0.0035)))
    painter.drawRoundedRect(rect, radius, radius)

    fill_ratio = 0.62
    if state in _ANIMATED_STATES:
        fill_ratio = 0.42 + 0.22 * (0.5 + 0.5 * math.sin(phase * math.tau))
    elif state is SystemState.RESTARTING:
        fill_ratio = 0.78
    elif state is SystemState.SHUTTING_DOWN:
        fill_ratio = 0.88
    elif state is SystemState.SUSPENDING:
        fill_ratio = 0.70

    inner = rect.adjusted(short * 0.008, short * 0.008, -short * 0.008, -short * 0.008)
    filled = QRectF(inner.left(), inner.top(), inner.width() * fill_ratio, inner.height())
    gradient = QLinearGradient(filled.left(), filled.center().y(), rect.right(), filled.center().y())
    gradient.setColorAt(0.0, QColor(palette.cyan))
    gradient.setColorAt(0.48, QColor(palette.green))
    gradient.setColorAt(1.0, QColor(palette.magenta))
    painter.setPen(Qt.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(filled, inner.height() / 2, inner.height() / 2)


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
    a narrow status bar and floor-like neon reflections. No reference raster or
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

    # Full-bleed rails deliberately replace the old rounded card. The reference
    # feels like one piece of hardware rather than a dialog drawn inside a panel.
    _draw_side_rails(painter, width, height, short, palette)

    if portrait:
        center = QPointF(width * 0.50, height * 0.35)
        diameter = width * 0.82
        _draw_hud_rings(painter, center, diameter, short, palette, state, phase)

        if not icon.isNull():
            icon_side = max(18, int(width * 0.085))
            target = QRectF(
                center.x() - icon_side / 2,
                center.y() - diameter * 0.23,
                icon_side,
                icon_side,
            )
            painter.setOpacity(0.82)
            painter.drawPixmap(target.toRect(), icon.pixmap(icon_side, icon_side))
            painter.setOpacity(1.0)

        _draw_gradient_wordmark(
            painter,
            image,
            QRectF(width * 0.10, center.y() - height * 0.025, width * 0.80, height * 0.055),
            palette,
            width * 0.095,
        )

        state_rect = QRectF(width * 0.09, center.y() + height * 0.045, width * 0.82, height * 0.055)
        _draw_centered(
            painter,
            image,
            state_rect,
            title.upper(),
            width * 0.052,
            accent.name(),
            bold=True,
        )
        if detail:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.12, center.y() + height * 0.094, width * 0.76, height * 0.038),
                detail,
                width * 0.034,
                palette.secondary,
            )

        bar = QRectF(width * 0.24, height * 0.535, width * 0.52, max(12.0, width * 0.035))
        _draw_progress_bar(painter, bar, short, palette, state, phase)

        context_y = height * 0.58
        if clock_text:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.12, context_y, width * 0.76, height * 0.050),
                clock_text,
                width * 0.070,
                palette.primary,
                bold=True,
            )
            context_y += height * 0.052
        if date_text and state is SystemState.LOCKED:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.15, context_y, width * 0.70, height * 0.030),
                date_text,
                width * 0.030,
                palette.secondary,
            )
            context_y += height * 0.036
        if sensor_text and state in _ANIMATED_STATES:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.08, context_y, width * 0.84, height * 0.035),
                sensor_text,
                width * 0.027,
                palette.muted,
            )

        # Tiny vertical telemetry ticks under the main ring mirror the reference
        # without competing with the state text.
        for index in range(17):
            x = width * 0.31 + index * width * 0.024
            color = QColor(palette.cyan if index < 6 else palette.green if index < 11 else palette.magenta)
            color.setAlpha(70 + (index % 4) * 28)
            painter.setPen(QPen(color, max(1.0, short * 0.003), Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(
                QPointF(x, height * 0.705),
                QPointF(x, height * (0.708 + 0.004 * (index % 3))),
            )

        _draw_floor_reflection(painter, width, height, short, palette)
        _draw_centered(
            painter,
            image,
            QRectF(width * 0.18, height * 0.925, width * 0.64, height * 0.026),
            f"{APP_NAME} · {__version__}",
            width * 0.022,
            palette.muted,
        )
    else:
        # Landscape screens use the same visual language but compress the HUD
        # vertically instead of falling back to a card-based layout.
        center = QPointF(width * 0.36, height * 0.48)
        diameter = min(height * 0.82, width * 0.42)
        _draw_hud_rings(painter, center, diameter, short, palette, state, phase)
        _draw_gradient_wordmark(
            painter,
            image,
            QRectF(width * 0.54, height * 0.23, width * 0.38, height * 0.16),
            palette,
            short * 0.13,
        )
        _draw_centered(
            painter,
            image,
            QRectF(width * 0.53, height * 0.41, width * 0.40, height * 0.14),
            title.upper(),
            short * 0.085,
            accent.name(),
            bold=True,
        )
        if detail:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.55, height * 0.54, width * 0.36, height * 0.09),
                detail,
                short * 0.045,
                palette.secondary,
            )
        bar = QRectF(width * 0.60, height * 0.69, width * 0.25, max(10.0, short * 0.035))
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
                QRectF(width * 0.52, height * 0.79, width * 0.42, height * 0.09),
                context,
                short * 0.038,
                palette.secondary,
            )

    painter.end()
    return image
