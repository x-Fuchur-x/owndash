"""Resolution-independent HUD screens for Linux system states."""
from __future__ import annotations

from dataclasses import dataclass
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QConicalGradient,
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
    bottom: str
    card: str
    border: str
    primary: str
    secondary: str
    muted: str
    glow: str
    accent2: str
    accent3: str


_THEMES = {
    "owndash": _Theme(
        top="#071827",
        bottom="#02060d",
        card="#06111d",
        border="#1d6fa5",
        primary="#f3fbff",
        secondary="#a9dfff",
        muted="#7893a8",
        glow="#21c8ff",
        accent2="#43ef8b",
        accent3="#ff2ba6",
    ),
    "bazzite-inspired": _Theme(
        top="#11112a",
        bottom="#050610",
        card="#0d0f22",
        border="#6057d8",
        primary="#f6f3ff",
        secondary="#c9c3ff",
        muted="#8e8aa9",
        glow="#6fd8ff",
        accent2="#7c6cff",
        accent3="#d253ff",
    ),
}

_STATE_ACCENTS = {
    SystemState.IDLE: "#4daec9",
    SystemState.LOCKED: "#4f8cff",
    SystemState.SUSPENDING: "#31c7ef",
    SystemState.SHUTTING_DOWN: "#e78d56",
    SystemState.RESTARTING: "#a57cff",
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


def _draw_state_mark(
    painter: QPainter,
    rect: QRectF,
    accent: QColor,
    icon: QIcon,
    state: SystemState,
) -> None:
    """Draw an OwnDash-owned center mark; no third-party branding assets."""
    if not icon.isNull():
        side = int(min(rect.width(), rect.height()) * 0.56)
        target = QRectF(
            rect.center().x() - side / 2,
            rect.center().y() - side / 2,
            side,
            side,
        )
        painter.drawPixmap(target.toRect(), icon.pixmap(side, side))
        return

    center = rect.center()
    radius = min(rect.width(), rect.height()) * 0.24
    pen = QPen(accent, max(2.0, radius * 0.085), Qt.SolidLine, Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    circle = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

    if state is SystemState.LOCKED:
        painter.drawRoundedRect(
            QRectF(center.x() - radius * 0.65, center.y() - radius * 0.05,
                   radius * 1.3, radius * 0.95),
            radius * 0.12,
            radius * 0.12,
        )
        painter.drawArc(
            QRectF(center.x() - radius * 0.43, center.y() - radius * 0.62,
                   radius * 0.86, radius * 0.86),
            0,
            180 * 16,
        )
    elif state is SystemState.RESTARTING:
        painter.drawArc(circle, 35 * 16, 285 * 16)
        p = QPointF(center.x() + radius * 0.72, center.y() - radius * 0.7)
        painter.drawLine(p, QPointF(p.x() - radius * 0.38, p.y() - radius * 0.05))
        painter.drawLine(p, QPointF(p.x() - radius * 0.06, p.y() + radius * 0.38))
    elif state is SystemState.SHUTTING_DOWN:
        painter.drawArc(circle, -45 * 16, 270 * 16)
        painter.drawLine(
            QPointF(center.x(), center.y() - radius * 1.08),
            QPointF(center.x(), center.y() + radius * 0.05),
        )
    elif state is SystemState.SUSPENDING:
        painter.drawArc(circle, 35 * 16, 285 * 16)
        painter.drawLine(
            QPointF(center.x() - radius * 0.22, center.y() - radius * 0.45),
            QPointF(center.x() + radius * 0.20, center.y() - radius * 0.45),
        )
        painter.drawLine(
            QPointF(center.x() - radius * 0.38, center.y() + radius * 0.05),
            QPointF(center.x() + radius * 0.38, center.y() + radius * 0.05),
        )
    else:  # IDLE
        painter.drawEllipse(circle)
        painter.drawPoint(center)


def _draw_tech_grid(painter: QPainter, card: QRectF, short: float, color: str) -> None:
    """Very subtle geometry that gives the state screen depth without assets."""
    grid = QColor(color)
    grid.setAlpha(18)
    painter.save()
    painter.setPen(QPen(grid, max(1.0, short * 0.0015)))
    step = max(22.0, short * 0.11)
    x = card.left() + step
    while x < card.right():
        painter.drawLine(QPointF(x, card.top()), QPointF(x, card.bottom()))
        x += step
    y = card.top() + step
    while y < card.bottom():
        painter.drawLine(QPointF(card.left(), y), QPointF(card.right(), y))
        y += step
    painter.restore()


def _draw_corner_brackets(painter: QPainter, card: QRectF, short: float, color: str) -> None:
    accent = QColor(color)
    accent.setAlpha(115)
    length = max(14.0, short * 0.08)
    inset = max(8.0, short * 0.025)
    painter.save()
    painter.setPen(QPen(accent, max(1.0, short * 0.004), Qt.SolidLine, Qt.RoundCap))
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x = card.left() + inset if sx > 0 else card.right() - inset
        y = card.top() + inset if sy > 0 else card.bottom() - inset
        painter.drawLine(QPointF(x, y), QPointF(x + sx * length, y))
        painter.drawLine(QPointF(x, y), QPointF(x, y + sy * length))
    painter.restore()


def _draw_hud(
    painter: QPainter,
    rect: QRectF,
    short: float,
    palette: _Theme,
    accent: QColor,
    icon: QIcon,
    state: SystemState,
    phase: float,
) -> None:
    """Draw a futuristic concentric HUD around the OwnDash/state mark."""
    center = rect.center()
    diameter = min(rect.width(), rect.height()) * 0.94
    base = QRectF(center.x() - diameter / 2, center.y() - diameter / 2, diameter, diameter)
    animated = state in _ANIMATED_STATES
    phase = float(phase % 1.0) if animated else 0.0
    rotation = phase * 360.0

    glow = QRadialGradient(center, diameter * 0.58)
    g0 = QColor(palette.glow)
    g0.setAlpha(48 if animated else 38)
    glow.setColorAt(0.0, g0)
    g1 = QColor(palette.glow)
    g1.setAlpha(0)
    glow.setColorAt(1.0, g1)
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(base.adjusted(-diameter * 0.10, -diameter * 0.10, diameter * 0.10, diameter * 0.10))
    painter.restore()

    # Faint continuous rings provide structure behind the segmented arcs.
    painter.save()
    faint = QColor(palette.secondary)
    faint.setAlpha(48)
    painter.setBrush(Qt.NoBrush)
    for scale in (0.98, 0.82, 0.66):
        r = diameter * scale
        ring = QRectF(center.x() - r / 2, center.y() - r / 2, r, r)
        painter.setPen(QPen(faint, max(1.0, short * 0.003)))
        painter.drawEllipse(ring)
    painter.restore()

    # Three differently phased segmented rings create movement using only a
    # handful of vector draw calls. Terminal/suspend screens freeze at phase 0.
    colors = (palette.glow, palette.accent2, palette.accent3)
    ring_scales = (0.92, 0.78, 0.69)
    segment_counts = (7, 9, 12)
    speeds = (1.0, -0.55, 0.32)
    for ring_index, (scale, count, speed) in enumerate(zip(ring_scales, segment_counts, speeds)):
        r = diameter * scale
        ring = QRectF(center.x() - r / 2, center.y() - r / 2, r, r)
        segment = 360.0 / count
        arc_span = segment * (0.48 if ring_index == 0 else 0.32)
        line_width = max(1.5, short * (0.010 - ring_index * 0.002))
        for index in range(count):
            color = QColor(colors[(index + ring_index) % len(colors)])
            color.setAlpha(215 if ring_index == 0 else 145)
            painter.setPen(QPen(color, line_width, Qt.SolidLine, Qt.RoundCap))
            start = index * segment + rotation * speed + ring_index * 17.0
            painter.drawArc(ring, int(start * 16), int(arc_span * 16))

    # HUD ticks. The highlighted tick walks around only in idle/lock mode.
    tick_radius = diameter * 0.49
    tick_inner = tick_radius - max(5.0, short * 0.025)
    highlighted = int(phase * 24.0) % 24 if animated else -1
    for index in range(24):
        angle = math.radians(index * 15.0 - 90.0)
        p1 = QPointF(center.x() + math.cos(angle) * tick_inner, center.y() + math.sin(angle) * tick_inner)
        p2 = QPointF(center.x() + math.cos(angle) * tick_radius, center.y() + math.sin(angle) * tick_radius)
        tick = QColor(palette.accent2 if index == highlighted else palette.secondary)
        tick.setAlpha(230 if index == highlighted else 74)
        painter.setPen(QPen(tick, max(1.0, short * (0.006 if index == highlighted else 0.003)), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(p1, p2)

    # State accent brackets visually bind the message to the HUD.
    bracket = QColor(accent)
    bracket.setAlpha(210)
    painter.setPen(QPen(bracket, max(1.5, short * 0.006), Qt.SolidLine, Qt.RoundCap))
    half = diameter * 0.18
    painter.drawLine(QPointF(center.x() - half, base.top() + diameter * 0.06), QPointF(center.x() + half, base.top() + diameter * 0.06))
    painter.drawLine(QPointF(center.x() - half, base.bottom() - diameter * 0.06), QPointF(center.x() + half, base.bottom() - diameter * 0.06))

    inner = QRectF(
        center.x() - diameter * 0.22,
        center.y() - diameter * 0.22,
        diameter * 0.44,
        diameter * 0.44,
    )
    _draw_state_mark(painter, inner, accent, icon, state)


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
    """Render one system-state frame.

    The renderer has no timers, I/O, or global state. ``animation_phase`` only
    changes IDLE/LOCKED vector geometry; terminal and suspend states stay fully
    deterministic so their final frame is safe to freeze while the PC sleeps.
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

    background = QLinearGradient(0, 0, width, height)
    background.setColorAt(0.0, QColor(palette.top))
    background.setColorAt(0.55, QColor(palette.card))
    background.setColorAt(1.0, QColor(palette.bottom))
    painter.fillRect(image.rect(), background)

    short = float(min(width, height))
    margin = max(10.0, short * 0.035)
    card = QRectF(margin, margin, width - 2 * margin, height - 2 * margin)
    card_color = QColor(palette.card)
    card_color.setAlpha(224)
    painter.setBrush(card_color)
    painter.setPen(QPen(QColor(palette.border), max(1.0, short * 0.004)))
    painter.drawRoundedRect(card, short * 0.045, short * 0.045)

    _draw_tech_grid(painter, card, short, palette.secondary)
    _draw_corner_brackets(painter, card, short, palette.glow)

    title, detail = _state_text(state, strings)
    portrait = height >= width * 1.35

    if portrait:
        hud_rect = QRectF(width * 0.07, height * 0.075, width * 0.86, height * 0.34)
        _draw_hud(painter, hud_rect, short, palette, accent, icon, state, phase)

        _draw_centered(
            painter, image,
            QRectF(width * 0.07, height * 0.425, width * 0.86, height * 0.085),
            title.upper(), width * 0.105, palette.primary, bold=True,
        )
        if detail:
            _draw_centered(
                painter, image,
                QRectF(width * 0.10, height * 0.505, width * 0.80, height * 0.055),
                detail, width * 0.050, palette.secondary,
            )

        y = 0.59
        if clock_text:
            _draw_centered(
                painter, image,
                QRectF(width * 0.10, height * y, width * 0.80, height * 0.085),
                clock_text, width * 0.090, palette.primary, bold=True,
            )
            y += 0.090
        if date_text and state is SystemState.LOCKED:
            _draw_centered(
                painter, image,
                QRectF(width * 0.10, height * y, width * 0.80, height * 0.052),
                date_text, width * 0.043, palette.secondary,
            )
            y += 0.060
        if sensor_text and state in _ANIMATED_STATES:
            _draw_centered(
                painter, image,
                QRectF(width * 0.08, height * y, width * 0.84, height * 0.055),
                sensor_text, width * 0.038, palette.muted,
            )

        # Small luminous divider echoes the supplied boot-image aesthetic while
        # remaining an original, resolution-independent vector element.
        divider = QLinearGradient(width * 0.22, 0, width * 0.78, 0)
        divider.setColorAt(0.0, QColor(palette.glow))
        divider.setColorAt(0.5, QColor(palette.accent2))
        divider.setColorAt(1.0, QColor(palette.accent3))
        painter.setPen(QPen(divider, max(2.0, short * 0.007), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(width * 0.28, height * 0.81), QPointF(width * 0.72, height * 0.81))

        _draw_centered(
            painter, image,
            QRectF(width * 0.10, height * 0.845, width * 0.80, height * 0.05),
            APP_NAME, width * 0.050, palette.secondary, bold=True,
        )
        _draw_centered(
            painter, image,
            QRectF(width * 0.10, height * 0.91, width * 0.80, height * 0.030),
            f"Version {__version__}", width * 0.027, palette.muted,
        )
    else:
        hud_rect = QRectF(width * 0.035, height * 0.08, width * 0.36, height * 0.84)
        _draw_hud(painter, hud_rect, short, palette, accent, icon, state, phase)
        text_x = width * 0.40
        text_w = width * 0.54
        _draw_centered(
            painter, image,
            QRectF(text_x, height * 0.16, text_w, height * 0.21),
            title.upper(), short * 0.135, palette.primary, bold=True,
        )
        if detail:
            _draw_centered(
                painter, image,
                QRectF(text_x, height * 0.385, text_w, height * 0.12),
                detail, short * 0.066, palette.secondary,
            )

        context = " · ".join(
            part for part in (
                clock_text or "",
                date_text if state is SystemState.LOCKED else "",
                sensor_text if state in _ANIMATED_STATES else "",
            ) if part
        )
        if context:
            _draw_centered(
                painter, image,
                QRectF(text_x, height * 0.54, text_w, height * 0.13),
                context, short * 0.055, palette.secondary,
            )
        _draw_centered(
            painter, image,
            QRectF(text_x, height * 0.73, text_w, height * 0.075),
            f"{APP_NAME} · Version {__version__}", short * 0.039, palette.muted,
        )

    painter.setPen(QPen(accent, max(2.0, short * 0.007), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(
        QPointF(card.left() + card.width() * 0.30, card.bottom() - short * 0.035),
        QPointF(card.right() - card.width() * 0.30, card.bottom() - short * 0.035),
    )
    painter.end()
    return image
