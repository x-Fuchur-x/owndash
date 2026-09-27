"""System-state artwork renderer with a single embedded portrait master."""
from __future__ import annotations

from dataclasses import dataclass

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
)

from owndash import APP_NAME
from owndash.core.system_state import SystemState

from .status_master import _master_image


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


_THEMES = {
    "owndash": _Theme("#06141f", "#020811", "#010307", "#f7fcff", "#b8d5e6", "#61798a", "#00e7ff", "#5af59a", "#ff2aae"),
    "bazzite-inspired": _Theme("#10142a", "#070919", "#02040d", "#f8f6ff", "#cbc8ff", "#8581a8", "#55d9ff", "#8d7cff", "#d95cff"),
}
_STATE_KEYS = {
    SystemState.IDLE: ("idle", ""),
    SystemState.LOCKED: ("system_locked", ""),
    SystemState.SUSPENDING: ("standby", "entering_standby"),
    SystemState.TRANSITIONING: ("system_transition", "ending_session"),
    SystemState.SHUTTING_DOWN: ("shutting_down", ""),
    SystemState.RESTARTING: ("restarting", ""),
}


def _fit_single_line_font(image: QImage, text: str, rect: QRectF, px: float, *, bold: bool = False, family: str = "DejaVu Sans") -> QFont:
    font = QFont(family)
    font.setBold(bold)
    font.setPixelSize(max(1, round(px)))
    while font.pixelSize() > 8:
        metrics = QFontMetricsF(font, image)
        if metrics.horizontalAdvance(text) <= rect.width() and metrics.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _draw_centered(p: QPainter, image: QImage, rect: QRectF, text: str, px: float, color: str, *, glow: str | None = None, bold: bool = False, tracking: float = 0.0) -> None:
    if not text:
        return
    font = _fit_single_line_font(image, text, rect, px, bold=bold)
    if tracking:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking)
        while font.pixelSize() > 8 and QFontMetricsF(font, image).horizontalAdvance(text) > rect.width():
            font.setPixelSize(font.pixelSize() - 1)
    p.save()
    p.setFont(font)
    flags = Qt.AlignCenter | Qt.AlignVCenter
    if glow:
        c = QColor(glow)
        for dx, dy, alpha in ((-2, 0, 20), (2, 0, 20), (0, -2, 20), (0, 2, 20), (0, 0, 62)):
            c.setAlpha(alpha)
            p.setPen(c)
            p.drawText(rect.translated(dx, dy), flags, text)
    p.setPen(QColor(color))
    p.drawText(rect, flags, text)
    p.restore()


def _portrait_state_copy(state: SystemState, title: str, detail: str) -> tuple[str, str]:
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
    return title.upper(), detail


def _state_text(state: SystemState, strings: dict[str, str]) -> tuple[str, str]:
    defaults = {
        "idle": "Idle",
        "system_locked": "System locked",
        "standby": "Standby",
        "entering_standby": "Entering standby",
        "system_transition": "System transition",
        "ending_session": "OwnDash is ending the current session.",
        "shutting_down": "Shutting down",
        "restarting": "Restarting",
    }
    title_key, detail_key = _STATE_KEYS[state]
    title = str(strings.get(title_key) or defaults[title_key])
    detail = str(strings.get(detail_key) or defaults.get(detail_key, "")) if detail_key else ""
    return title, detail


def _load_master(width: int, height: int) -> QImage:
    image = _master_image().copy()
    if image.width() != width or image.height() != height:
        image = image.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return image.convertToFormat(QImage.Format_RGB32)


def _draw_clock_and_date(p: QPainter, image: QImage, width: int, height: int, clock_text: str | None, date_text: str | None) -> None:
    if clock_text:
        _draw_centered(p, image, QRectF(width * .12, height * .566, width * .76, height * .062), clock_text, width * .108, "#f8fdff", glow="#00e7ff")
    if date_text:
        _draw_centered(p, image, QRectF(width * .16, height * .625, width * .68, height * .034), date_text, width * .034, "#b8d5e6")


def _draw_state_icon(p: QPainter, rect: QRectF, state: SystemState) -> None:
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#f7fcff"), max(2.0, rect.width() * .055), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    c = rect.center()
    if state is SystemState.SHUTTING_DOWN:
        p.drawArc(QRectF(x + w * .18, y + h * .18, w * .64, h * .64), 40 * 16, 280 * 16)
        p.drawLine(QPointF(c.x(), y + h * .08), QPointF(c.x(), y + h * .46))
    elif state is SystemState.RESTARTING:
        p.drawArc(QRectF(x + w * .17, y + h * .17, w * .66, h * .66), 30 * 16, 285 * 16)
        p.drawLine(QPointF(x + w * .74, y + h * .15), QPointF(x + w * .82, y + h * .36))
        p.drawLine(QPointF(x + w * .82, y + h * .36), QPointF(x + w * .62, y + h * .31))
    elif state in (SystemState.SUSPENDING, SystemState.IDLE):
        p.drawArc(QRectF(x + w * .20, y + h * .15, w * .58, h * .70), 70 * 16, 220 * 16)
        p.drawArc(QRectF(x + w * .34, y + h * .13, w * .46, h * .68), 105 * 16, 170 * 16)
    else:
        for offset in (-.22, 0, .22):
            p.drawEllipse(QPointF(c.x() + w * offset, c.y()), w * .055, w * .055)
    p.restore()


def _draw_dynamic_portrait_state(p: QPainter, image: QImage, state: SystemState, title: str, detail: str) -> None:
    w, h = image.width(), image.height()
    headline, state_detail = _portrait_state_copy(state, title, detail)
    rect = QRectF(w * .09, h * .365, w * .82, h * .205)
    bg = QLinearGradient(0, rect.top(), 0, rect.bottom())
    bg.setColorAt(0, QColor(0, 8, 14, 245))
    bg.setColorAt(.5, QColor(0, 5, 10, 252))
    bg.setColorAt(1, QColor(0, 7, 12, 245))
    p.fillRect(rect, bg)
    _draw_state_icon(p, QRectF(w * .40, h * .382, w * .20, h * .055), state)
    _draw_centered(p, image, QRectF(w * .08, h * .445, w * .84, h * .052), headline, w * .096, "#f7fcff", glow="#00e7ff", tracking=max(1.0, w * .010))
    _draw_centered(p, image, QRectF(w * .12, h * .500, w * .76, h * .030), state_detail, w * .038, "#c9d8e4", tracking=max(.5, w * .003))
    bar = QRectF(w * .16, h * .545, w * .68, max(7.0, w * .014))
    y = bar.center().y()
    grad = QLinearGradient(bar.left(), y, bar.right(), y)
    grad.setColorAt(0, QColor("#00e7ff"))
    grad.setColorAt(.52, QColor("#5c89ff"))
    grad.setColorAt(1, QColor("#ff2aae"))
    p.setPen(QPen(QBrush(grad), max(3.0, bar.height() * .55), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(bar.left(), y), QPointF(bar.right(), y))


def _render_landscape(width: int, height: int, state: SystemState, theme: str, title: str, detail: str, clock_text: str | None) -> QImage:
    pal = _THEMES.get(str(theme), _THEMES["owndash"])
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(pal.bottom))
    p = QPainter(image)
    bg = QLinearGradient(0, 0, width, height)
    bg.setColorAt(0, QColor(pal.top))
    bg.setColorAt(.5, QColor(pal.middle))
    bg.setColorAt(1, QColor(pal.bottom))
    p.fillRect(image.rect(), bg)
    _draw_centered(p, image, QRectF(width * .10, height * .20, width * .80, height * .18), APP_NAME, min(width, height) * .13, pal.primary, glow=pal.cyan, bold=True)
    _draw_centered(p, image, QRectF(width * .10, height * .43, width * .80, height * .16), title.upper(), min(width, height) * .085, pal.primary, glow=pal.magenta, bold=True)
    if detail:
        _draw_centered(p, image, QRectF(width * .15, height * .60, width * .70, height * .10), detail, min(width, height) * .042, pal.secondary)
    if clock_text:
        _draw_centered(p, image, QRectF(width * .35, height * .76, width * .30, height * .10), clock_text, min(width, height) * .055, pal.secondary)
    p.end()
    return image


def render_system_state_image(width: int, height: int, state: SystemState, theme: str, icon: QIcon, strings: dict[str, str], *, clock_text: str | None = None, date_text: str | None = None, sensor_text: str | None = None, animation_phase: float = 0.0) -> QImage:
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")
    if state is SystemState.ACTIVE:
        raise ValueError("ACTIVE has no temporary system-state frame")
    if state not in _STATE_KEYS:
        raise ValueError(f"unsupported system state: {state}")

    title, detail = _state_text(state, strings)
    if height < width * 1.35:
        return _render_landscape(width, height, state, theme, title, detail, clock_text)

    image = _load_master(width, height)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    if state is not SystemState.LOCKED:
        _draw_dynamic_portrait_state(p, image, state, title, detail)
    _draw_clock_and_date(p, image, width, height, clock_text, date_text if state is SystemState.LOCKED else None)
    if state is SystemState.LOCKED:
        phase_tick = int((float(animation_phase) % 1.0) * 7.0)
        edge = image.pixelColor(width - 1, height - 1)
        image.setPixelColor(width - 1, height - 1, QColor(edge.red(), edge.green(), min(255, edge.blue() + phase_tick)))
    if state is SystemState.IDLE:
        phase = float(animation_phase % 1.0)
        x = width * (.17 + .66 * phase)
        y = height * .553
        c = QColor("#00e7ff")
        c.setAlpha(150)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawEllipse(QPointF(x, y), max(2.0, width * .009), max(2.0, width * .009))
    p.end()
    return image
