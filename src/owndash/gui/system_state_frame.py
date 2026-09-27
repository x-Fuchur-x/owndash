"""Unified OwnDash system-state and disconnected-screen renderer.

The portrait renderer deliberately follows one approved OwnDash HUD geometry.
All state variations share that geometry and differ only in copy, symbol and
accent treatment.  There is no legacy/master-art fallback path.
"""
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
    QPainterPath,
    QPen,
    QRadialGradient,
)

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


@dataclass(frozen=True, slots=True)
class _StateStyle:
    left: str
    right: str
    glow: str
    symbol: str


_THEMES = {
    "owndash": _Theme(
        "#061827", "#020811", "#000205", "#f8fcff", "#e0edf6", "#7692a5",
        "#00eaff", "#ff32df",
    ),
    "bazzite-inspired": _Theme(
        "#10162f", "#050718", "#01030a", "#fbf9ff", "#ddd9ff", "#8b86b0",
        "#51dcff", "#b86dff",
    ),
}

_STATE_KEYS = {
    SystemState.IDLE: ("idle", ""),
    SystemState.LOCKED: ("system_locked", ""),
    SystemState.SUSPENDING: ("standby", "entering_standby"),
    SystemState.TRANSITIONING: ("system_transition", "ending_session"),
    SystemState.SHUTTING_DOWN: ("shutting_down", ""),
    SystemState.RESTARTING: ("restarting", ""),
}

_STATE_STYLES = {
    SystemState.LOCKED: _StateStyle("#00eaff", "#ff35e5", "#25dfff", "locked"),
    SystemState.IDLE: _StateStyle("#00eaff", "#78ff36", "#2df4b4", "idle"),
    SystemState.SUSPENDING: _StateStyle("#ffd525", "#ff7b22", "#ffb11e", "standby"),
    SystemState.TRANSITIONING: _StateStyle("#4fd8ff", "#8072ff", "#5faeff", "transition"),
    SystemState.SHUTTING_DOWN: _StateStyle("#ff334d", "#ff673a", "#ff4052", "shutdown"),
    SystemState.RESTARTING: _StateStyle("#8068ff", "#ff45dc", "#a75cff", "restart"),
}


def _theme(name: str) -> _Theme:
    return _THEMES.get(str(name), _THEMES["owndash"])


def _mix(a: QColor, b: QColor, amount: float) -> QColor:
    t = max(0.0, min(1.0, amount))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


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


def _draw_text(
    p: QPainter,
    image: QImage,
    rect: QRectF,
    text: str,
    px: float,
    color: str,
    *,
    bold: bool = False,
    tracking: float = 0.0,
    glow: str | None = None,
) -> None:
    if not text:
        return
    font = _fit_font(image, text, rect, px, bold=bold, tracking=tracking)
    p.save()
    p.setFont(font)
    flags = Qt.AlignCenter | Qt.AlignVCenter
    if glow:
        halo = QColor(glow)
        for spread, alpha in ((5, 18), (3, 34), (1, 80)):
            halo.setAlpha(alpha)
            p.setPen(QPen(halo, spread))
            p.drawText(rect, flags, text)
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
    english = any(token in lowered for token in ("locked", "shutting", "restart", "transition", "idle", "standby"))
    if state is SystemState.LOCKED:
        return ("LOCKED", "System is locked") if english else ("GESPERRT", "System ist gesperrt")
    if state is SystemState.IDLE:
        return ("IDLE", "System is idle") if english else ("LEERLAUF", "System ist im Leerlauf")
    if state is SystemState.SUSPENDING:
        return ("STANDBY", "System is entering standby") if english else ("STANDBY", "System ist im Standby")
    if state is SystemState.TRANSITIONING:
        return ("TRANSITION", "Ending current session") if english else ("SYSTEMWECHSEL", "Aktuelle Sitzung wird beendet")
    if state is SystemState.SHUTTING_DOWN:
        return ("SHUTTING DOWN", "System is shutting down") if english else ("HERUNTERFAHREN", "System wird heruntergefahren")
    if state is SystemState.RESTARTING:
        return ("RESTARTING", "System is restarting") if english else ("NEUSTART", "System startet neu")
    return title.upper(), detail


def _glow_pen(color: QColor, width: float, alpha: int) -> QPen:
    c = QColor(color)
    c.setAlpha(alpha)
    return QPen(c, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _draw_glow_path(p: QPainter, path: QPainterPath, color: QColor, width: float) -> None:
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(_glow_pen(color, width * 5.2, 18))
    p.drawPath(path)
    p.setPen(_glow_pen(color, width * 2.8, 42))
    p.drawPath(path)
    p.setPen(_glow_pen(color, width, 235))
    p.drawPath(path)
    p.restore()


def _draw_glow_line(p: QPainter, a: QPointF, b: QPointF, color: QColor, width: float) -> None:
    path = QPainterPath(a)
    path.lineTo(b)
    _draw_glow_path(p, path, color, width)


def _draw_ambient_background(p: QPainter, image: QImage, pal: _Theme, style: _StateStyle) -> None:
    w, h = image.width(), image.height()
    bg = QLinearGradient(0, 0, 0, h)
    bg.setColorAt(0.0, QColor(pal.top))
    bg.setColorAt(0.25, QColor(pal.middle))
    bg.setColorAt(0.72, QColor("#01040a"))
    bg.setColorAt(1.0, QColor(pal.bottom))
    p.fillRect(image.rect(), bg)

    # Cool atmospheric halo at the top and a restrained state glow around the HUD.
    top = QRadialGradient(QPointF(w * .50, h * .05), w * .80)
    top.setColorAt(0.0, QColor(0, 122, 190, 90))
    top.setColorAt(0.45, QColor(0, 52, 85, 35))
    top.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillRect(image.rect(), top)

    state_glow = QRadialGradient(QPointF(w * .50, h * .34), w * .62)
    c = QColor(style.glow)
    c.setAlpha(42)
    state_glow.setColorAt(0.0, c)
    c2 = QColor(style.glow)
    c2.setAlpha(0)
    state_glow.setColorAt(1.0, c2)
    p.fillRect(image.rect(), state_glow)


def _draw_side_frame(p: QPainter, image: QImage, left: QColor, right: QColor) -> None:
    w, h = image.width(), image.height()
    sx, sy = w / 480.0, h / 1920.0

    def pt(x: float, y: float) -> QPointF:
        return QPointF(x * sx, y * sy)

    # Main angular rails deliberately use the same anchor points for every state.
    left_path = QPainterPath(pt(44, 0))
    for x, y in ((44, 80), (68, 112), (68, 270), (48, 310), (48, 1390), (70, 1430), (70, 1660), (48, 1692), (48, 1780)):
        left_path.lineTo(pt(x, y))
    right_path = QPainterPath(pt(436, 0))
    for x, y in ((436, 80), (412, 112), (412, 270), (432, 310), (432, 1390), (410, 1430), (410, 1660), (432, 1692), (432, 1780)):
        right_path.lineTo(pt(x, y))
    _draw_glow_path(p, left_path, left, max(1.5, w * .0042))
    _draw_glow_path(p, right_path, right, max(1.5, w * .0042))

    # Secondary rails add the dense layered look that was missing from the old renderer.
    for offset, alpha in ((-17, 85), (12, 55)):
        lc = QColor(left)
        rc = QColor(right)
        lc.setAlpha(alpha)
        rc.setAlpha(alpha)
        _draw_glow_line(p, pt(48 + offset, 320), pt(48 + offset, 1372), lc, max(1.0, w * .0022))
        _draw_glow_line(p, pt(432 - offset, 320), pt(432 - offset, 1372), rc, max(1.0, w * .0022))

    # Top and lower side pods with indicator LEDs.
    p.save()
    p.setBrush(QColor(1, 5, 10, 235))
    p.setPen(Qt.NoPen)
    for x, is_left in ((0, True), (442, False)):
        pod = QRectF(x * sx, 95 * sy, 38 * sx, 185 * sy)
        p.drawRoundedRect(pod, 4 * sx, 4 * sx)
        pod2 = QRectF(x * sx, 1450 * sy, 38 * sx, 170 * sy)
        p.drawRoundedRect(pod2, 4 * sx, 4 * sx)
        color = left if is_left else right
        for base_y in (130, 1480):
            for i in range(5):
                cc = QColor(color)
                cc.setAlpha(235 - i * 18)
                p.setBrush(cc)
                p.drawEllipse(QPointF((28 if is_left else 452) * sx, (base_y + i * 22) * sy), 3.2 * sx, 3.2 * sx)
    p.restore()


def _draw_brand(p: QPainter, image: QImage, icon: QIcon, pal: _Theme) -> None:
    w, h = image.width(), image.height()
    if h >= w * 1.35:
        sx, sy = w / 480.0, h / 1920.0
        icon_rect = QRectF(185 * sx, 105 * sy, 110 * sx, 110 * sx)
        pix = _effective_icon(icon).pixmap(max(1, round(icon_rect.width())), max(1, round(icon_rect.height())))
        p.drawPixmap(icon_rect.toRect(), pix)
        _draw_text(p, image, QRectF(95 * sx, 248 * sy, 290 * sx, 42 * sy), "SYSTEM DASHBOARD", 17 * sx, pal.primary, tracking=5.5 * sx)
    else:
        s = min(w, h)
        icon_rect = QRectF(w * .055, h * .08, s * .18, s * .18)
        pix = _effective_icon(icon).pixmap(max(1, round(icon_rect.width())), max(1, round(icon_rect.height())))
        p.drawPixmap(icon_rect.toRect(), pix)
        _draw_text(p, image, QRectF(w * .25, h * .08, w * .38, h * .16), APP_NAME, s * .085, pal.primary, bold=True)


def _ring_color(left: QColor, right: QColor, angle_deg: float) -> QColor:
    # left half trends cyan/state-left, right half trends state-right.
    x = math.cos(math.radians(angle_deg))
    return _mix(left, right, (x + 1.0) / 2.0)


def _draw_ring(p: QPainter, image: QImage, rect: QRectF, style: _StateStyle, phase: float, *, animate: bool) -> None:
    left = QColor(style.left)
    right = QColor(style.right)
    cx, cy = rect.center().x(), rect.center().y()
    d = rect.width()
    p.save()
    p.setBrush(Qt.NoBrush)

    # Atmospheric bloom behind the ring.
    bloom = QRadialGradient(rect.center(), d * .62)
    bloom_left = QColor(left)
    bloom_left.setAlpha(42)
    bloom.setColorAt(0.0, QColor(0, 0, 0, 0))
    bloom.setColorAt(.58, bloom_left)
    bloom.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setBrush(bloom)
    p.setPen(Qt.NoPen)
    p.drawEllipse(rect.adjusted(-d * .10, -d * .10, d * .10, d * .10))
    p.setBrush(Qt.NoBrush)

    # Fine outer concentric lines.
    for inset, alpha, width in ((-.035, 72, .004), (.00, 120, .006), (.045, 80, .004), (.105, 90, .004), (.175, 62, .003)):
        rr = rect.adjusted(d * inset, d * inset, -d * inset, -d * inset)
        grad = QConicalGradient(rr.center(), -90)
        l = QColor(left); l.setAlpha(alpha)
        r = QColor(right); r.setAlpha(alpha)
        grad.setColorAt(0.0, r)
        grad.setColorAt(.48, l)
        grad.setColorAt(1.0, r)
        p.setPen(QPen(grad, max(1.0, d * width)))
        p.drawEllipse(rr)

    # Twelve heavy segmented arcs form the main approved HUD ring.
    arc_rect = rect.adjusted(d * .06, d * .06, -d * .06, -d * .06)
    for i in range(12):
        angle = -90 + i * 30
        color = _ring_color(left, right, angle)
        # subtle glow under each segment
        glow = QColor(color); glow.setAlpha(45)
        p.setPen(QPen(glow, max(10.0, d * .075), Qt.SolidLine, Qt.FlatCap))
        p.drawArc(arc_rect, int((-angle - 7) * 16), int(-18 * 16))
        p.setPen(QPen(color, max(6.0, d * .048), Qt.SolidLine, Qt.FlatCap))
        p.drawArc(arc_rect, int((-angle - 7) * 16), int(-18 * 16))

    # Dense dotted/tick ring.
    r0 = d * .355
    r1 = d * .385
    for i in range(72):
        angle = i * 5.0 - 90.0
        a = math.radians(angle)
        color = _ring_color(left, right, angle)
        major = (i % 6 == 0)
        inner = r0 - (d * .018 if major else 0.0)
        outer = r1 + (d * .012 if major else 0.0)
        p.setPen(QPen(color, max(1.1, d * (.010 if major else .006)), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx + inner * math.cos(a), cy + inner * math.sin(a)), QPointF(cx + outer * math.cos(a), cy + outer * math.sin(a)))

    # Inner luminous ring.
    inner_rect = rect.adjusted(d * .255, d * .255, -d * .255, -d * .255)
    grad = QConicalGradient(inner_rect.center(), -90)
    grad.setColorAt(0.0, right)
    grad.setColorAt(.50, left)
    grad.setColorAt(1.0, right)
    p.setPen(QPen(grad, max(3.0, d * .018)))
    p.drawEllipse(inner_rect)
    faint = QColor(style.glow); faint.setAlpha(45)
    p.setPen(QPen(faint, max(9.0, d * .045)))
    p.drawEllipse(inner_rect)

    # Cardinal crosshair lines.
    for deg in (0, 90, 180, 270):
        a = math.radians(deg)
        color = _ring_color(left, right, deg)
        p.setPen(QPen(color, max(1.5, d * .007), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx + d * .42 * math.cos(a), cy + d * .42 * math.sin(a)), QPointF(cx + d * .54 * math.cos(a), cy + d * .54 * math.sin(a)))

    # A restrained moving highlight: only idle/locked animate in production.
    if animate:
        start_angle = (phase % 1.0) * 360.0 - 90.0
        hi = QColor("#ffffff")
        hi.setAlpha(190)
        rr = rect.adjusted(d * .025, d * .025, -d * .025, -d * .025)
        p.setPen(QPen(hi, max(2.0, d * .010), Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rr, int((-start_angle) * 16), int(-24 * 16))

    p.restore()


def _draw_symbol_stroke(p: QPainter, draw_fn, color: QColor, width: float) -> None:
    p.save()
    for mul, alpha in ((3.8, 26), (2.2, 60), (1.0, 245)):
        c = QColor(color); c.setAlpha(alpha)
        p.setPen(QPen(c, width * mul, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        draw_fn()
    p.restore()


def _draw_state_symbol(p: QPainter, image: QImage, rect: QRectF, kind: str, color: str) -> None:
    c = QColor(color)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    center = rect.center()
    width = max(2.0, w * .055)

    if kind == "locked":
        def draw():
            body = QRectF(x + w * .22, y + h * .43, w * .56, h * .42)
            p.drawRoundedRect(body, w * .07, w * .07)
            p.drawArc(QRectF(x + w * .31, y + h * .12, w * .38, h * .53), 0, 180 * 16)
            p.drawLine(QPointF(center.x(), y + h * .58), QPointF(center.x(), y + h * .72))
        _draw_symbol_stroke(p, draw, c, width)
    elif kind in ("idle", "standby"):
        def draw_moon():
            p.drawArc(QRectF(x + w * .18, y + h * .13, w * .62, h * .72), 65 * 16, 235 * 16)
            p.drawArc(QRectF(x + w * .38, y + h * .08, w * .46, h * .70), 110 * 16, 170 * 16)
        _draw_symbol_stroke(p, draw_moon, c, width)
        if kind == "idle":
            _draw_text(p, image, QRectF(x + w * .60, y + h * .08, w * .33, h * .36), "Z", w * .18, color, bold=True, glow=color)
            _draw_text(p, image, QRectF(x + w * .52, y + h * .28, w * .25, h * .28), "z", w * .12, color, bold=True, glow=color)
    elif kind == "shutdown":
        def draw_power():
            p.drawArc(QRectF(x + w * .17, y + h * .17, w * .66, h * .66), 40 * 16, 280 * 16)
            p.drawLine(QPointF(center.x(), y + h * .08), QPointF(center.x(), y + h * .47))
        _draw_symbol_stroke(p, draw_power, c, width)
    elif kind == "restart":
        def draw_restart():
            p.drawArc(QRectF(x + w * .15, y + h * .18, w * .68, h * .64), 25 * 16, 132 * 16)
            p.drawArc(QRectF(x + w * .17, y + h * .18, w * .68, h * .64), 205 * 16, 132 * 16)
            p.drawLine(QPointF(x + w * .72, y + h * .13), QPointF(x + w * .84, y + h * .34))
            p.drawLine(QPointF(x + w * .84, y + h * .34), QPointF(x + w * .62, y + h * .31))
            p.drawLine(QPointF(x + w * .28, y + h * .87), QPointF(x + w * .16, y + h * .66))
            p.drawLine(QPointF(x + w * .16, y + h * .66), QPointF(x + w * .38, y + h * .69))
        _draw_symbol_stroke(p, draw_restart, c, width)
    elif kind == "disconnected":
        def draw_disconnect():
            p.drawRoundedRect(QRectF(x + w * .13, y + h * .20, w * .62, h * .45), w * .04, w * .04)
            p.drawLine(QPointF(x + w * .32, y + h * .78), QPointF(x + w * .62, y + h * .78))
            p.drawLine(QPointF(x + w * .47, y + h * .65), QPointF(x + w * .47, y + h * .78))
            p.drawLine(QPointF(x + w * .28, y + h * .73), QPointF(x + w * .76, y + h * .23))
        _draw_symbol_stroke(p, draw_disconnect, c, width)
    else:
        _draw_text(p, image, rect, "•••", w * .22, color, bold=True, glow=color)


def _draw_status_bar(p: QPainter, image: QImage, left: QColor, right: QColor, y: float) -> None:
    w = image.width()
    sx = w / 480.0
    x0, x1 = 75 * sx, 405 * sx
    p.save()
    outline = QColor(left); outline.setAlpha(170)
    p.setPen(QPen(outline, max(1.0, 1.2 * sx)))
    p.drawLine(QPointF(x0, y), QPointF(x1, y))
    grad = QLinearGradient(135 * sx, y, 345 * sx, y)
    grad.setColorAt(0.0, left)
    grad.setColorAt(.50, _mix(left, right, .5))
    grad.setColorAt(1.0, right)
    p.setPen(QPen(grad, max(4.0, 8 * sx), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(135 * sx, y), QPointF(345 * sx, y))
    p.restore()


def _draw_floor(p: QPainter, image: QImage, left: QColor, right: QColor) -> None:
    w, h = image.width(), image.height()
    sx, sy = w / 480.0, h / 1920.0
    horizon = 1718 * sy

    # Curved console lip.
    lip = QPainterPath(QPointF(48 * sx, 1695 * sy))
    lip.quadTo(QPointF(240 * sx, 1635 * sy), QPointF(432 * sx, 1695 * sy))
    _draw_glow_path(p, lip, _mix(left, right, .45), max(1.4, 1.8 * sx))
    for x, color in ((140, left), (240, _mix(left, right, .48)), (340, right)):
        _draw_glow_line(p, QPointF(x * sx, 1670 * sy), QPointF(x * sx, horizon), color, max(1.0, 1.3 * sx))

    # Horizon and reflective perspective grid.
    _draw_glow_line(p, QPointF(0, horizon), QPointF(w, horizon), _mix(left, right, .5), max(1.0, 1.2 * sx))
    p.save()
    for i in range(1, 8):
        t = i / 8.0
        yy = horizon + (h - horizon) * (t ** 1.7)
        c = _mix(left, right, t)
        c.setAlpha(95 - i * 6)
        p.setPen(QPen(c, max(.7, .9 * sx)))
        p.drawLine(QPointF(0, yy), QPointF(w, yy))
    van = QPointF(w * .50, horizon)
    for x in (-120, 0, 90, 175, 305, 390, 480, 600):
        end = QPointF(x * sx, h)
        color = left if x < 240 else right
        cc = QColor(color); cc.setAlpha(110)
        p.setPen(QPen(cc, max(.7, .9 * sx)))
        p.drawLine(van, end)
    p.restore()

    # Soft reflected light columns.
    for x, color in ((140, left), (240, _mix(left, right, .45)), (340, right)):
        grad = QLinearGradient(x * sx, horizon, x * sx, h)
        cc = QColor(color); cc.setAlpha(70)
        grad.setColorAt(0.0, cc)
        cc2 = QColor(color); cc2.setAlpha(0)
        grad.setColorAt(1.0, cc2)
        p.fillRect(QRectF((x - 32) * sx, horizon, 64 * sx, h - horizon), grad)


def _render_portrait(
    width: int,
    height: int,
    *,
    theme: str,
    icon: QIcon,
    headline: str,
    detail: str,
    style: _StateStyle,
    clock_text: str | None,
    date_text: str | None,
    sensor_text: str | None,
    animation_phase: float,
    animate_ring: bool,
    footer_text: str | None,
) -> QImage:
    pal = _theme(theme)
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(pal.bottom))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    left = QColor(style.left)
    right = QColor(style.right)
    _draw_ambient_background(p, image, pal, style)
    _draw_side_frame(p, image, left, right)
    _draw_brand(p, image, icon, pal)

    sx, sy = width / 480.0, height / 1920.0
    ring = QRectF(48 * sx, 318 * sy, 384 * sx, 384 * sx)
    _draw_ring(p, image, ring, style, animation_phase, animate=animate_ring)
    symbol_rect = ring.adjusted(ring.width() * .33, ring.height() * .33, -ring.width() * .33, -ring.height() * .33)
    _draw_state_symbol(p, image, symbol_rect, style.symbol, "#f9fdff")

    # Separator flare underneath the ring.
    sep_y = 758 * sy
    _draw_glow_line(p, QPointF(90 * sx, sep_y), QPointF(390 * sx, sep_y), _mix(left, right, .5), max(1.0, 1.3 * sx))

    title_color = pal.primary
    title_glow = style.glow if style.symbol in ("shutdown", "restart") else None
    _draw_text(p, image, QRectF(45 * sx, 875 * sy, 390 * sx, 115 * sy), headline, 49 * sx, title_color, bold=True, tracking=3.2 * sx, glow=title_glow)
    _draw_text(p, image, QRectF(55 * sx, 995 * sy, 370 * sx, 65 * sy), detail, 23 * sx, pal.secondary, tracking=2.0 * sx)
    _draw_status_bar(p, image, left, right, 1100 * sy)

    if sensor_text:
        _draw_text(p, image, QRectF(70 * sx, 1125 * sy, 340 * sx, 42 * sy), sensor_text, 14 * sx, pal.muted)

    if clock_text:
        _draw_text(p, image, QRectF(90 * sx, 1215 * sy, 300 * sx, 105 * sy), clock_text, 62 * sx, pal.primary, bold=True, glow=style.glow)
    if date_text:
        _draw_text(p, image, QRectF(105 * sx, 1310 * sy, 270 * sx, 62 * sy), date_text, 26 * sx, pal.secondary, tracking=4.0 * sx)

    footer = footer_text or f"OwnDash {__version__}"
    _draw_text(p, image, QRectF(110 * sx, 1608 * sy, 260 * sx, 55 * sy), footer, 15 * sx, pal.secondary)
    _draw_floor(p, image, left, right)

    p.end()
    return image


def _render_landscape(
    width: int,
    height: int,
    *,
    theme: str,
    icon: QIcon,
    headline: str,
    detail: str,
    style: _StateStyle,
    clock_text: str | None,
    date_text: str | None,
    animation_phase: float,
    animate_ring: bool,
    footer_text: str | None,
) -> QImage:
    pal = _theme(theme)
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(pal.bottom))
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    _draw_ambient_background(p, image, pal, style)
    s = min(width, height)
    ring = QRectF(width * .07, height * .13, s * .72, s * .72)
    _draw_ring(p, image, ring, style, animation_phase, animate=animate_ring)
    symbol_rect = ring.adjusted(ring.width() * .34, ring.height() * .34, -ring.width() * .34, -ring.height() * .34)
    _draw_state_symbol(p, image, symbol_rect, style.symbol, "#f9fdff")
    _draw_text(p, image, QRectF(width * .42, height * .22, width * .52, height * .20), headline, s * .105, pal.primary, bold=True, glow=style.glow)
    _draw_text(p, image, QRectF(width * .43, height * .43, width * .50, height * .12), detail, s * .045, pal.secondary)
    if clock_text:
        _draw_text(p, image, QRectF(width * .46, height * .62, width * .28, height * .13), clock_text, s * .065, pal.primary, bold=True)
    if date_text:
        _draw_text(p, image, QRectF(width * .46, height * .74, width * .32, height * .08), date_text, s * .030, pal.secondary)
    _draw_text(p, image, QRectF(width * .70, height * .91, width * .27, height * .05), footer_text or f"OwnDash {__version__}", s * .024, pal.muted)
    p.end()
    return image


def _render_family(
    width: int,
    height: int,
    *,
    theme: str,
    icon: QIcon,
    headline: str,
    detail: str,
    style: _StateStyle,
    clock_text: str | None,
    date_text: str | None,
    sensor_text: str | None,
    animation_phase: float,
    animate_ring: bool,
    footer_text: str | None = None,
) -> QImage:
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")
    if height >= width * 1.35:
        return _render_portrait(
            width, height, theme=theme, icon=icon, headline=headline, detail=detail,
            style=style, clock_text=clock_text, date_text=date_text,
            sensor_text=sensor_text, animation_phase=animation_phase,
            animate_ring=animate_ring, footer_text=footer_text,
        )
    return _render_landscape(
        width, height, theme=theme, icon=icon, headline=headline, detail=detail,
        style=style, clock_text=clock_text, date_text=date_text,
        animation_phase=animation_phase, animate_ring=animate_ring,
        footer_text=footer_text,
    )


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
    style = _STATE_STYLES[state]
    animate = state in (SystemState.LOCKED, SystemState.IDLE)
    phase = float(animation_phase) if animate else 0.0
    return _render_family(
        width, height, theme=theme, icon=icon, headline=headline,
        detail=state_detail, style=style, clock_text=clock_text,
        date_text=date_text, sensor_text=sensor_text,
        animation_phase=phase, animate_ring=animate,
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
    style = _StateStyle("#00eaff", "#ff35e5", "#24dfff", "disconnected")
    return _render_family(
        int(width), int(height), theme=theme, icon=icon, headline=headline,
        detail=combined_detail, style=style, clock_text=None, date_text=None,
        sensor_text=None, animation_phase=0.0, animate_ring=False,
        footer_text=f"OwnDash {__version__}",
    )
