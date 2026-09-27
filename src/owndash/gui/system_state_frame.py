"""Unified OwnDash system-state and disconnected-screen renderer."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QImage, QLinearGradient, QPainter, QPen

from owndash import APP_NAME, __version__
from owndash.assets import app_icon_path
from owndash.core.system_state import SystemState


@dataclass(frozen=True, slots=True)
class _Theme:
    top: str
    middle: str
    bottom: str
    primary: str
    secondary: str
    muted: str
    rail_left: str
    rail_right: str


_THEMES = {
    "owndash": _Theme("#06111d", "#030812", "#010307", "#f7fcff", "#bad3e4", "#597083", "#00e7ff", "#ff2aae"),
    "bazzite-inspired": _Theme("#11142b", "#07091a", "#02040d", "#faf8ff", "#cbc8ff", "#7f7ba5", "#55d9ff", "#c56cff"),
}

_STATE_KEYS = {
    SystemState.IDLE: ("idle", ""),
    SystemState.LOCKED: ("system_locked", ""),
    SystemState.SUSPENDING: ("standby", "entering_standby"),
    SystemState.TRANSITIONING: ("system_transition", "ending_session"),
    SystemState.SHUTTING_DOWN: ("shutting_down", ""),
    SystemState.RESTARTING: ("restarting", ""),
}

_STATE_ACCENTS = {
    SystemState.LOCKED: "#00dfff",
    SystemState.IDLE: "#35f0a3",
    SystemState.SUSPENDING: "#ffb447",
    SystemState.TRANSITIONING: "#6ea8ff",
    SystemState.SHUTTING_DOWN: "#ff4f5f",
    SystemState.RESTARTING: "#b66cff",
}


def _theme(name: str) -> _Theme:
    return _THEMES.get(str(name), _THEMES["owndash"])


def _fit_font(image: QImage, text: str, rect: QRectF, px: float, *, bold: bool = False, tracking: float = 0.0) -> QFont:
    font = QFont("DejaVu Sans")
    font.setBold(bold)
    font.setPixelSize(max(1, round(px)))
    if tracking:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking)
    while font.pixelSize() > 7:
        metrics = QFontMetricsF(font, image)
        if metrics.horizontalAdvance(text) <= rect.width() and metrics.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _draw_text(p: QPainter, image: QImage, rect: QRectF, text: str, px: float, color: str, *, bold: bool = False, tracking: float = 0.0, glow: str | None = None) -> None:
    if not text:
        return
    font = _fit_font(image, text, rect, px, bold=bold, tracking=tracking)
    p.save()
    p.setFont(font)
    flags = Qt.AlignCenter | Qt.AlignVCenter
    if glow:
        halo = QColor(glow)
        for dx, dy, alpha in ((-2, 0, 20), (2, 0, 20), (0, -2, 20), (0, 2, 20), (0, 0, 55)):
            halo.setAlpha(alpha)
            p.setPen(halo)
            p.drawText(rect.translated(dx, dy), flags, text)
    p.setPen(QColor(color))
    p.drawText(rect, flags, text)
    p.restore()


def _effective_icon(icon: QIcon) -> QIcon:
    if not icon.isNull():
        return icon
    with app_icon_path() as path:
        return QIcon(str(path))


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


def _portrait_copy(state: SystemState, title: str, detail: str) -> tuple[str, str]:
    lowered = title.strip().lower()
    english = any(token in lowered for token in ("locked", "shutting", "restart", "transition", "idle"))
    if state is SystemState.LOCKED:
        return ("LOCKED", "System is locked") if english else ("GESPERRT", "System ist gesperrt")
    if state is SystemState.IDLE:
        return ("ACTIVE", "Waiting for activity") if english else ("AKTIV", "Warten auf Aktivität")
    if state is SystemState.SUSPENDING:
        return ("STANDBY", "Entering standby") if english else ("STANDBY", "Standby wird vorbereitet")
    if state is SystemState.TRANSITIONING:
        return ("TRANSITION", "Ending current session") if english else ("SYSTEMWECHSEL", "Aktuelle Sitzung wird beendet")
    if state is SystemState.SHUTTING_DOWN:
        return ("SHUTTING DOWN", "System is shutting down safely") if english else ("HERUNTERFAHREN", "System wird sicher beendet")
    if state is SystemState.RESTARTING:
        return ("RESTARTING", "System is restarting") if english else ("NEUSTART", "System wird neu gestartet")
    return title.upper(), detail


def _draw_background(p: QPainter, image: QImage, pal: _Theme) -> None:
    w, h = image.width(), image.height()
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0.0, QColor(pal.top))
    bg.setColorAt(0.46, QColor(pal.middle))
    bg.setColorAt(1.0, QColor(pal.bottom))
    p.fillRect(image.rect(), bg)

    # Subtle tech rails and horizon structure: visible enough to feel premium,
    # quiet enough that the ring remains the single focal point.
    rail = max(1.5, w * 0.004)
    left = QColor(pal.rail_left)
    right = QColor(pal.rail_right)
    left.setAlpha(150)
    right.setAlpha(140)
    p.setPen(QPen(left, rail))
    p.drawLine(QPointF(w * .045, h * .055), QPointF(w * .045, h * .78))
    p.setPen(QPen(right, rail))
    p.drawLine(QPointF(w * .955, h * .055), QPointF(w * .955, h * .78))

    for frac, alpha in ((.79, 105), (.82, 75), (.85, 50)):
        c = QColor(pal.rail_left)
        c.setAlpha(alpha)
        p.setPen(QPen(c, max(1.0, w * .002)))
        p.drawLine(QPointF(w * .12, h * frac), QPointF(w * .88, h * frac))


def _draw_brand(p: QPainter, image: QImage, icon: QIcon, pal: _Theme) -> None:
    w, h = image.width(), image.height()
    if h >= w * 1.35:
        icon_rect = QRectF(w * .26, h * .055, w * .16, w * .16)
        text_rect = QRectF(w * .42, h * .055, w * .38, w * .16)
        subtitle_rect = QRectF(w * .20, h * .132, w * .60, h * .026)
    else:
        s = min(w, h)
        icon_rect = QRectF(w * .055, h * .08, s * .19, s * .19)
        text_rect = QRectF(icon_rect.right() + s * .035, h * .075, w * .31, s * .20)
        subtitle_rect = QRectF(w * .055, h * .31, w * .36, h * .08)

    pix = _effective_icon(icon).pixmap(max(1, round(icon_rect.width())), max(1, round(icon_rect.height())))
    p.drawPixmap(icon_rect.toRect(), pix)
    _draw_text(p, image, text_rect, APP_NAME, max(14.0, w * .083 if h >= w * 1.35 else min(w, h) * .105), pal.primary, bold=True)
    _draw_text(p, image, subtitle_rect, "SYSTEM DASHBOARD", max(9.0, w * .026 if h >= w * 1.35 else min(w, h) * .034), pal.secondary, tracking=max(.3, w * .003))


def _draw_ring(p: QPainter, image: QImage, rect: QRectF, accent: str, phase: float, *, animate: bool) -> None:
    base = QColor(accent)
    muted = QColor(accent)
    muted.setAlpha(42)
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(muted, max(2.0, rect.width() * .026)))
    p.drawEllipse(rect)

    inset = rect.adjusted(rect.width() * .06, rect.height() * .06, -rect.width() * .06, -rect.height() * .06)
    muted2 = QColor(accent)
    muted2.setAlpha(85)
    p.setPen(QPen(muted2, max(1.0, rect.width() * .008)))
    p.drawEllipse(inset)

    cx, cy = rect.center().x(), rect.center().y()
    outer = rect.width() * .56
    inner = rect.width() * .49
    p.setPen(QPen(QColor(accent), max(1.0, rect.width() * .008), Qt.SolidLine, Qt.RoundCap))
    for i in range(24):
        import math
        a = math.radians(i * 15.0)
        p.drawLine(QPointF(cx + inner * math.cos(a), cy + inner * math.sin(a)), QPointF(cx + outer * math.cos(a), cy + outer * math.sin(a)))

    start = int((90.0 - ((phase % 1.0) * 360.0 if animate else 0.0)) * 16)
    p.setPen(QPen(base, max(3.0, rect.width() * .028), Qt.SolidLine, Qt.RoundCap))
    p.drawArc(rect.adjusted(rect.width() * .015, rect.height() * .015, -rect.width() * .015, -rect.height() * .015), start, -112 * 16)
    glow = QColor(accent)
    glow.setAlpha(65)
    p.setPen(QPen(glow, max(6.0, rect.width() * .05), Qt.SolidLine, Qt.RoundCap))
    p.drawArc(rect.adjusted(rect.width() * .015, rect.height() * .015, -rect.width() * .015, -rect.height() * .015), start, -112 * 16)
    p.restore()


def _draw_state_symbol(p: QPainter, rect: QRectF, kind: str, color: str) -> None:
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(color), max(2.0, rect.width() * .065), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    c = rect.center()

    if kind == "locked":
        body = QRectF(x + w * .22, y + h * .43, w * .56, h * .42)
        p.drawRoundedRect(body, w * .06, w * .06)
        p.drawArc(QRectF(x + w * .31, y + h * .13, w * .38, h * .50), 0, 180 * 16)
        p.drawLine(QPointF(c.x(), y + h * .58), QPointF(c.x(), y + h * .71))
    elif kind == "idle":
        p.drawEllipse(QRectF(x + w * .16, y + h * .16, w * .68, h * .68))
        p.drawLine(QPointF(x + w * .33, y + h * .52), QPointF(x + w * .46, y + h * .65))
        p.drawLine(QPointF(x + w * .46, y + h * .65), QPointF(x + w * .70, y + h * .37))
    elif kind == "standby":
        p.drawArc(QRectF(x + w * .22, y + h * .13, w * .60, h * .72), 70 * 16, 225 * 16)
        p.drawArc(QRectF(x + w * .37, y + h * .12, w * .46, h * .70), 108 * 16, 175 * 16)
    elif kind == "shutdown":
        p.drawArc(QRectF(x + w * .17, y + h * .17, w * .66, h * .66), 40 * 16, 280 * 16)
        p.drawLine(QPointF(c.x(), y + h * .08), QPointF(c.x(), y + h * .47))
    elif kind == "restart":
        p.drawArc(QRectF(x + w * .17, y + h * .17, w * .66, h * .66), 30 * 16, 285 * 16)
        p.drawLine(QPointF(x + w * .73, y + h * .14), QPointF(x + w * .83, y + h * .36))
        p.drawLine(QPointF(x + w * .83, y + h * .36), QPointF(x + w * .61, y + h * .31))
    elif kind == "disconnected":
        screen = QRectF(x + w * .16, y + h * .20, w * .68, h * .49)
        p.drawRoundedRect(screen, w * .04, w * .04)
        p.drawLine(QPointF(x + w * .35, y + h * .80), QPointF(x + w * .65, y + h * .80))
        p.drawLine(QPointF(c.x(), y + h * .69), QPointF(c.x(), y + h * .80))
        p.drawLine(QPointF(x + w * .37, y + h * .35), QPointF(x + w * .63, y + h * .55))
        p.drawLine(QPointF(x + w * .63, y + h * .35), QPointF(x + w * .37, y + h * .55))
    else:
        for offset in (-.22, 0, .22):
            p.drawEllipse(QPointF(c.x() + w * offset, c.y()), w * .055, w * .055)
    p.restore()


def _render_family(
    width: int,
    height: int,
    *,
    theme: str,
    icon: QIcon,
    headline: str,
    detail: str,
    accent: str,
    symbol: str,
    clock_text: str | None,
    date_text: str | None,
    sensor_text: str | None,
    animation_phase: float,
    animate_ring: bool,
    footer_text: str | None = None,
) -> QImage:
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")
    pal = _theme(theme)
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(pal.bottom))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    _draw_background(p, image, pal)
    _draw_brand(p, image, icon, pal)

    portrait = height >= width * 1.35
    if portrait:
        ring = QRectF(width * .17, height * .205, width * .66, width * .66)
        symbol_rect = ring.adjusted(ring.width() * .27, ring.height() * .27, -ring.width() * .27, -ring.height() * .27)
        _draw_ring(p, image, ring, accent, animation_phase, animate=animate_ring)
        _draw_state_symbol(p, symbol_rect, symbol, accent)

        _draw_text(p, image, QRectF(width * .07, height * .405, width * .86, height * .07), headline, width * .105, pal.primary, bold=True, tracking=max(.8, width * .004), glow=accent)
        _draw_text(p, image, QRectF(width * .10, height * .472, width * .80, height * .055), detail, width * .044, pal.secondary)
        if sensor_text:
            _draw_text(p, image, QRectF(width * .12, height * .525, width * .76, height * .035), sensor_text, width * .030, pal.muted)

        line = QColor(accent)
        line.setAlpha(180)
        p.setPen(QPen(line, max(1.0, width * .004)))
        p.drawLine(QPointF(width * .25, height * .575), QPointF(width * .75, height * .575))

        if clock_text:
            _draw_text(p, image, QRectF(width * .12, height * .61, width * .76, height * .07), clock_text, width * .115, pal.primary, bold=True, glow=accent)
        if date_text:
            _draw_text(p, image, QRectF(width * .13, height * .68, width * .74, height * .035), date_text, width * .034, pal.secondary)

        # Decorative lower HUD/horizon, deliberately vector-only so no old artwork can leak back.
        horizon_y = height * .79
        p.setPen(QPen(QColor(pal.rail_left), max(1.0, width * .003)))
        p.drawLine(QPointF(width * .08, horizon_y), QPointF(width * .92, horizon_y))
        ridge = [(.08, .79), (.19, .765), (.30, .782), (.42, .752), (.53, .774), (.67, .744), (.79, .770), (.92, .756)]
        accent_c = QColor(accent)
        accent_c.setAlpha(150)
        p.setPen(QPen(accent_c, max(1.2, width * .004)))
        for (x1, y1), (x2, y2) in zip(ridge, ridge[1:]):
            p.drawLine(QPointF(width * x1, height * y1), QPointF(width * x2, height * y2))

        footer = footer_text or f"OwnDash {__version__}"
        _draw_text(p, image, QRectF(width * .08, height * .94, width * .84, height * .028), footer, width * .025, pal.muted)
    else:
        s = min(width, height)
        ring = QRectF(width * .08, height * .22, s * .55, s * .55)
        symbol_rect = ring.adjusted(ring.width() * .28, ring.height() * .28, -ring.width() * .28, -ring.height() * .28)
        _draw_ring(p, image, ring, accent, animation_phase, animate=animate_ring)
        _draw_state_symbol(p, symbol_rect, symbol, accent)
        _draw_text(p, image, QRectF(width * .42, height * .28, width * .52, height * .16), headline, s * .095, pal.primary, bold=True, glow=accent)
        _draw_text(p, image, QRectF(width * .43, height * .46, width * .50, height * .12), detail, s * .047, pal.secondary)
        if clock_text:
            _draw_text(p, image, QRectF(width * .44, height * .64, width * .34, height * .10), clock_text, s * .060, pal.primary, bold=True)
        if date_text:
            _draw_text(p, image, QRectF(width * .44, height * .74, width * .36, height * .07), date_text, s * .030, pal.secondary)
        _draw_text(p, image, QRectF(width * .69, height * .90, width * .27, height * .045), footer_text or f"OwnDash {__version__}", s * .025, pal.muted)

    p.end()
    return image


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
    width, height = int(width), int(height)
    if state is SystemState.ACTIVE:
        raise ValueError("ACTIVE has no temporary system-state frame")
    if state not in _STATE_KEYS:
        raise ValueError(f"unsupported system state: {state}")

    title, detail = _state_text(state, strings)
    headline, state_detail = _portrait_copy(state, title, detail)
    symbol = {
        SystemState.LOCKED: "locked",
        SystemState.IDLE: "idle",
        SystemState.SUSPENDING: "standby",
        SystemState.TRANSITIONING: "transition",
        SystemState.SHUTTING_DOWN: "shutdown",
        SystemState.RESTARTING: "restart",
    }[state]
    animate = state in (SystemState.LOCKED, SystemState.IDLE)
    phase = float(animation_phase) if animate else 0.0
    return _render_family(
        width,
        height,
        theme=theme,
        icon=icon,
        headline=headline,
        detail=state_detail,
        accent=_STATE_ACCENTS[state],
        symbol=symbol,
        clock_text=clock_text,
        date_text=date_text,
        sensor_text=sensor_text,
        animation_phase=phase,
        animate_ring=animate,
    )


def render_disconnected_status_image(
    width: int,
    height: int,
    icon: QIcon,
    *,
    status: str = "OwnDash disconnected",
    detail: str = "No active connection to OwnDash",
    farewell: str = "See you soon.",
    theme: str = "owndash",
) -> QImage:
    headline = str(status or "OwnDash disconnected").upper()
    combined_detail = str(detail or farewell or "")
    if farewell and farewell not in combined_detail:
        combined_detail = f"{combined_detail} · {farewell}" if combined_detail else farewell
    return _render_family(
        int(width),
        int(height),
        theme=theme,
        icon=icon,
        headline=headline,
        detail=combined_detail,
        accent="#7d7cff",
        symbol="disconnected",
        clock_text=None,
        date_text=None,
        sensor_text=None,
        animation_phase=0.0,
        animate_ring=False,
        footer_text=f"OwnDash {__version__}",
    )
