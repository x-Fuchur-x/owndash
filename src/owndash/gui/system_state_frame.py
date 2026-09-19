"""Resolution-independent, static screens for Linux system states."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
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
    bottom: str
    card: str
    border: str
    primary: str
    secondary: str
    muted: str
    glow: str


_THEMES = {
    "owndash": _Theme(
        top="#071827",
        bottom="#030810",
        card="#081423",
        border="#1d6fa5",
        primary="#f3fbff",
        secondary="#a9dfff",
        muted="#7893a8",
        glow="#21c8ff",
    ),
    "bazzite-inspired": _Theme(
        top="#11112a",
        bottom="#060711",
        card="#101124",
        border="#6057d8",
        primary="#f6f3ff",
        secondary="#c9c3ff",
        muted="#8e8aa9",
        glow="#7569ff",
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
    """Draw a lightweight OwnDash-owned state mark; no third-party assets."""
    if not icon.isNull():
        side = int(min(rect.width(), rect.height()) * 0.62)
        target = QRectF(
            rect.center().x() - side / 2,
            rect.center().y() - side / 2,
            side,
            side,
        )
        painter.drawPixmap(target.toRect(), icon.pixmap(side, side))
        return

    center = rect.center()
    radius = min(rect.width(), rect.height()) * 0.26
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
) -> QImage:
    """Render one static frame for a non-active system state.

    The function has no timers, I/O, or global state. It is intentionally
    deterministic and cheap enough to call only when the visible state changes.
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
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(palette.bottom))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    background = QLinearGradient(0, 0, width, height)
    background.setColorAt(0.0, QColor(palette.top))
    background.setColorAt(1.0, QColor(palette.bottom))
    painter.fillRect(image.rect(), background)

    short = float(min(width, height))
    margin = max(10.0, short * 0.045)
    card = QRectF(margin, margin, width - 2 * margin, height - 2 * margin)
    painter.setBrush(QColor(palette.card))
    painter.setPen(QPen(QColor(palette.border), max(1.0, short * 0.004)))
    painter.drawRoundedRect(card, short * 0.045, short * 0.045)

    # Static glow is inexpensive and makes both themes readable on small panels.
    glow_center = QPointF(width * 0.50, height * (0.22 if height > width else 0.50))
    glow_radius = max(short * 0.65, 1.0)
    glow = QRadialGradient(glow_center, glow_radius)
    glow_color = QColor(palette.glow)
    glow_color.setAlpha(52)
    glow.setColorAt(0.0, glow_color)
    transparent = QColor(palette.glow)
    transparent.setAlpha(0)
    glow.setColorAt(1.0, transparent)
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawRoundedRect(card, short * 0.045, short * 0.045)
    painter.restore()

    title, detail = _state_text(state, strings)
    portrait = height >= width * 1.35

    if portrait:
        mark_rect = QRectF(width * 0.12, height * 0.08, width * 0.76, height * 0.24)
        _draw_state_mark(painter, mark_rect, accent, icon, state)

        _draw_centered(
            painter, image,
            QRectF(width * 0.08, height * 0.34, width * 0.84, height * 0.105),
            title, width * 0.125, palette.primary, bold=True,
        )
        if detail:
            _draw_centered(
                painter, image,
                QRectF(width * 0.10, height * 0.455, width * 0.80, height * 0.075),
                detail, width * 0.060, palette.secondary,
            )

        y = 0.56
        if clock_text:
            _draw_centered(
                painter, image,
                QRectF(width * 0.10, height * y, width * 0.80, height * 0.10),
                clock_text, width * 0.105, palette.primary, bold=True,
            )
            y += 0.105
        if date_text and state is SystemState.LOCKED:
            _draw_centered(
                painter, image,
                QRectF(width * 0.10, height * y, width * 0.80, height * 0.065),
                date_text, width * 0.052, palette.secondary,
            )
            y += 0.075
        if sensor_text and state in {SystemState.IDLE, SystemState.LOCKED}:
            _draw_centered(
                painter, image,
                QRectF(width * 0.08, height * y, width * 0.84, height * 0.065),
                sensor_text, width * 0.043, palette.muted,
            )

        _draw_centered(
            painter, image,
            QRectF(width * 0.10, height * 0.865, width * 0.80, height * 0.055),
            APP_NAME, width * 0.055, palette.secondary, bold=True,
        )
        _draw_centered(
            painter, image,
            QRectF(width * 0.10, height * 0.93, width * 0.80, height * 0.035),
            f"Version {__version__}", width * 0.030, palette.muted,
        )
    else:
        mark_rect = QRectF(width * 0.055, height * 0.15, width * 0.30, height * 0.70)
        _draw_state_mark(painter, mark_rect, accent, icon, state)
        text_x = width * 0.38
        text_w = width * 0.55
        _draw_centered(
            painter, image,
            QRectF(text_x, height * 0.18, text_w, height * 0.22),
            title, short * 0.15, palette.primary, bold=True,
        )
        if detail:
            _draw_centered(
                painter, image,
                QRectF(text_x, height * 0.405, text_w, height * 0.13),
                detail, short * 0.075, palette.secondary,
            )

        context = " · ".join(
            part for part in (
                clock_text or "",
                date_text if state is SystemState.LOCKED else "",
                sensor_text if state in {SystemState.IDLE, SystemState.LOCKED} else "",
            ) if part
        )
        if context:
            _draw_centered(
                painter, image,
                QRectF(text_x, height * 0.55, text_w, height * 0.13),
                context, short * 0.060, palette.secondary,
            )
        _draw_centered(
            painter, image,
            QRectF(text_x, height * 0.72, text_w, height * 0.08),
            f"{APP_NAME} · Version {__version__}", short * 0.042, palette.muted,
        )

    # A subtle state-colored bottom rule guarantees terminal states remain
    # visually distinguishable even when localized titles happen to be similar.
    painter.setPen(QPen(accent, max(2.0, short * 0.008), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(
        QPointF(card.left() + card.width() * 0.25, card.bottom() - short * 0.04),
        QPointF(card.right() - card.width() * 0.25, card.bottom() - short * 0.04),
    )
    painter.end()
    return image
