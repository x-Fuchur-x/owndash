"""Unified OwnDash system-state renderer based on the approved neon HUD master.

The 480x1920 portrait artwork is the visual source of truth. State changes are
created from that single master by palette treatment plus small dynamic overlays
for symbol, localized copy, clock/date and the restrained ring animation.
There is no legacy portrait renderer or visual fallback path.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from importlib.resources import as_file, files

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QImage, QLinearGradient, QPainter, QPen, QRadialGradient

from owndash import __version__
from owndash.core.system_state import SystemState


_MASTER_W = 480
_MASTER_H = 1920
_MASTER_RESOURCE = files("owndash").joinpath("assets", "status_hud_master.jpg")

_STATE_KEYS = {
    SystemState.IDLE: ("idle", ""),
    SystemState.LOCKED: ("system_locked", ""),
    SystemState.SUSPENDING: ("standby", "entering_standby"),
    SystemState.TRANSITIONING: ("system_transition", "ending_session"),
    SystemState.SHUTTING_DOWN: ("shutting_down", ""),
    SystemState.RESTARTING: ("restarting", ""),
}

# left, right, symbol, palette treatment
_STATE_STYLE = {
    SystemState.LOCKED: ("#00eaff", "#ff35e5", "locked", "original"),
    SystemState.IDLE: ("#00eaff", "#72ff35", "idle", "full"),
    SystemState.SUSPENDING: ("#ffd126", "#ff7d20", "standby", "full"),
    SystemState.TRANSITIONING: ("#36cfff", "#8068ff", "transition", "ring"),
    SystemState.SHUTTING_DOWN: ("#ff334d", "#ff7036", "shutdown", "ring"),
    SystemState.RESTARTING: ("#8068ff", "#ff45dc", "restart", "ring"),
}


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


def _hex_rgb(value: str) -> tuple[int, int, int]:
    c = QColor(value)
    return c.red(), c.green(), c.blue()


def _lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


@lru_cache(maxsize=1)
def _master_pil() -> Image.Image:
    with as_file(_MASTER_RESOURCE) as path:
        return Image.open(path).convert("RGB").copy()


def _tint_master(source: Image.Image, left: str, right: str) -> Image.Image:
    gray = ImageOps.grayscale(source).convert("RGB")
    a, b = _hex_rgb(left), _hex_rgb(right)
    ramp = Image.new("RGB", (_MASTER_W, 1))
    px = ramp.load()
    for x in range(_MASTER_W):
        px[x, 0] = _lerp_rgb(a, b, x / (_MASTER_W - 1))
    ramp = ramp.resize(source.size)
    tinted = ImageChops.multiply(gray, ramp)
    return Image.blend(tinted, source, 0.10)


@lru_cache(maxsize=8)
def _master_variant(left: str, right: str, treatment: str) -> QImage:
    source = _master_pil()
    if treatment == "original":
        result = source.copy()
    else:
        tinted = _tint_master(source, left, right)
        if treatment == "full":
            result = tinted
        else:
            result = source.copy()
            mask = Image.new("L", source.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((18, 280, 462, 950), fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(26))
            result.paste(tinted, (0, 0), mask)

    # The original application mark is never recolored or regenerated.
    logo_crop = source.crop((135, 55, 345, 320))
    result.paste(logo_crop, (135, 55))

    data = result.tobytes("raw", "RGB")
    return QImage(data, result.width, result.height, result.width * 3, QImage.Format_RGB888).copy().convertToFormat(QImage.Format_RGB32)


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


def _draw_text(p: QPainter, image: QImage, rect: QRectF, text: str, px: float, color: QColor, *, bold: bool = False, tracking: float = 0.0, glow: QColor | None = None) -> None:
    if not text:
        return
    font = _fit_font(image, text, rect, px, bold=bold, tracking=tracking)
    p.save()
    p.setFont(font)
    flags = Qt.AlignCenter | Qt.AlignVCenter
    if glow is not None:
        for width, alpha in ((8, 14), (4, 28), (2, 65)):
            halo = QColor(glow)
            halo.setAlpha(alpha)
            p.setPen(QPen(halo, width))
            p.drawText(rect, flags, text)
    p.setPen(color)
    p.drawText(rect, flags, text)
    p.restore()


def _dark_patch(p: QPainter, rect: QRectF, *, alpha: int = 248) -> None:
    g = QLinearGradient(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
    g.setColorAt(0.0, QColor(0, 5, 11, max(0, alpha - 8)))
    g.setColorAt(0.5, QColor(0, 3, 8, alpha))
    g.setColorAt(1.0, QColor(0, 5, 11, max(0, alpha - 8)))
    p.fillRect(rect, g)


def _erase_center_symbol(p: QPainter, sx: float, sy: float) -> None:
    center = QPointF(240 * sx, 655 * sy)
    radius = 78 * sx
    grad = QRadialGradient(center, radius)
    grad.setColorAt(0.0, QColor(0, 4, 9, 255))
    grad.setColorAt(0.72, QColor(0, 5, 10, 252))
    grad.setColorAt(1.0, QColor(0, 5, 10, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawEllipse(center, radius, radius)


def _draw_symbol_stroke(p: QPainter, draw_fn, color: QColor, width: float) -> None:
    p.save()
    p.setBrush(Qt.NoBrush)
    for mul, alpha in ((4.2, 24), (2.2, 58), (1.0, 250)):
        c = QColor(color)
        c.setAlpha(alpha)
        p.setPen(QPen(c, width * mul, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        draw_fn()
    p.restore()


def _draw_state_symbol(p: QPainter, rect: QRectF, kind: str, color: QColor) -> None:
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    c = rect.center()
    width = max(2.0, w * .055)

    if kind == "locked":
        def draw():
            body = QRectF(x + w * .22, y + h * .43, w * .56, h * .42)
            p.drawRoundedRect(body, w * .07, w * .07)
            p.drawArc(QRectF(x + w * .31, y + h * .12, w * .38, h * .53), 0, 180 * 16)
            p.drawLine(QPointF(c.x(), y + h * .58), QPointF(c.x(), y + h * .72))
        _draw_symbol_stroke(p, draw, color, width)
    elif kind == "idle":
        def moon():
            p.drawArc(QRectF(x + w * .18, y + h * .13, w * .62, h * .72), 65 * 16, 235 * 16)
            p.drawArc(QRectF(x + w * .38, y + h * .08, w * .46, h * .70), 110 * 16, 170 * 16)
        _draw_symbol_stroke(p, moon, color, width)
        p.save()
        p.setPen(QPen(color, max(2.0, width * .70), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(x+w*.69,y+h*.26), QPointF(x+w*.86,y+h*.26))
        p.drawLine(QPointF(x+w*.86,y+h*.26), QPointF(x+w*.69,y+h*.43))
        p.drawLine(QPointF(x+w*.69,y+h*.43), QPointF(x+w*.86,y+h*.43))
        p.drawLine(QPointF(x+w*.61,y+h*.43), QPointF(x+w*.73,y+h*.43))
        p.drawLine(QPointF(x+w*.73,y+h*.43), QPointF(x+w*.61,y+h*.55))
        p.drawLine(QPointF(x+w*.61,y+h*.55), QPointF(x+w*.73,y+h*.55))
        p.restore()
    elif kind == "standby":
        def moon():
            p.drawArc(QRectF(x + w * .18, y + h * .13, w * .62, h * .72), 65 * 16, 235 * 16)
            p.drawArc(QRectF(x + w * .38, y + h * .08, w * .46, h * .70), 110 * 16, 170 * 16)
        _draw_symbol_stroke(p, moon, color, width)
    elif kind == "shutdown":
        def power():
            p.drawArc(QRectF(x + w * .17, y + h * .17, w * .66, h * .66), 40 * 16, 280 * 16)
            p.drawLine(QPointF(c.x(), y + h * .08), QPointF(c.x(), y + h * .47))
        _draw_symbol_stroke(p, power, color, width)
    elif kind == "restart":
        def restart():
            p.drawArc(QRectF(x + w * .15, y + h * .18, w * .68, h * .64), 25 * 16, 132 * 16)
            p.drawArc(QRectF(x + w * .17, y + h * .18, w * .68, h * .64), 205 * 16, 132 * 16)
            p.drawLine(QPointF(x + w * .72, y + h * .13), QPointF(x + w * .84, y + h * .34))
            p.drawLine(QPointF(x + w * .84, y + h * .34), QPointF(x + w * .62, y + h * .31))
            p.drawLine(QPointF(x + w * .28, y + h * .87), QPointF(x + w * .16, y + h * .66))
            p.drawLine(QPointF(x + w * .16, y + h * .66), QPointF(x + w * .38, y + h * .69))
        _draw_symbol_stroke(p, restart, color, width)
    elif kind == "disconnected":
        def disconnected():
            p.drawRoundedRect(QRectF(x + w * .12, y + h * .20, w * .61, h * .44), w * .04, w * .04)
            p.drawLine(QPointF(x + w * .31, y + h * .78), QPointF(x + w * .61, y + h * .78))
            p.drawLine(QPointF(x + w * .46, y + h * .64), QPointF(x + w * .46, y + h * .78))
            p.drawLine(QPointF(x + w * .28, y + h * .73), QPointF(x + w * .78, y + h * .22))
        _draw_symbol_stroke(p, disconnected, color, width)
    else:
        p.save()
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        for offset in (-.22, 0, .22):
            p.drawEllipse(QPointF(c.x() + w * offset, c.y()), w * .055, w * .055)
        p.restore()


def _draw_status_bar(p: QPainter, sx: float, sy: float, left: QColor, right: QColor) -> None:
    y = 1210 * sy
    p.save()
    outline = QColor(left)
    outline.setAlpha(175)
    p.setPen(QPen(outline, max(1.0, 1.1 * sx)))
    p.drawLine(QPointF(75 * sx, y), QPointF(405 * sx, y))
    grad = QLinearGradient(135 * sx, y, 345 * sx, y)
    grad.setColorAt(0.0, left)
    grad.setColorAt(.5, QColor(70, 150, 255))
    grad.setColorAt(1.0, right)
    p.setPen(QPen(grad, max(4.0, 9 * sx), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(135 * sx, y), QPointF(345 * sx, y))
    p.restore()


def _draw_animation_sweep(p: QPainter, sx: float, sy: float, phase: float, left: QColor, right: QColor) -> None:
    # One slow 28-degree highlight on the outer ring; it never alters layout.
    rect = QRectF(42 * sx, 323 * sy, 396 * sx, 620 * sy)
    start = int((90.0 - (phase % 1.0) * 360.0) * 16)
    grad = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    grad.setColorAt(0.0, left)
    grad.setColorAt(1.0, right)
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 65), max(7.0, 12 * sx), Qt.SolidLine, Qt.RoundCap))
    p.drawArc(rect, start, -28 * 16)
    p.setPen(QPen(grad, max(2.0, 3 * sx), Qt.SolidLine, Qt.RoundCap))
    p.drawArc(rect, start, -28 * 16)
    p.restore()


def _render_master_family(width: int, height: int, *, headline: str, detail: str, left_hex: str, right_hex: str, symbol: str, treatment: str, clock_text: str | None, date_text: str | None, sensor_text: str | None, animation_phase: float, animate_ring: bool, footer_text: str | None = None) -> QImage:
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")

    master = _master_variant(left_hex, right_hex, treatment)
    image = master.copy() if (width, height) == (_MASTER_W, _MASTER_H) else master.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    image = image.convertToFormat(QImage.Format_RGB32)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    sx, sy = width / _MASTER_W, height / _MASTER_H
    left, right = QColor(left_hex), QColor(right_hex)
    white = QColor("#f9fdff")

    # Remove only baked dynamic content; approved rails/ring/floor stay untouched.
    _erase_center_symbol(p, sx, sy)
    _dark_patch(p, QRectF(54 * sx, 985 * sy, 372 * sx, 250 * sy))
    _dark_patch(p, QRectF(98 * sx, 1288 * sy, 284 * sx, 190 * sy))
    _dark_patch(p, QRectF(128 * sx, 1590 * sy, 224 * sx, 82 * sy), alpha=238)

    symbol_rect = QRectF(175 * sx, 545 * sy, 130 * sx, 185 * sy)
    _draw_state_symbol(p, symbol_rect, symbol, white)

    glow = QColor(left_hex if symbol != "restart" else right_hex)
    _draw_text(p, image, QRectF(42 * sx, 1008 * sy, 396 * sx, 92 * sy), headline, 51 * sx, white, bold=True, tracking=4.0 * sx, glow=glow if symbol in ("shutdown", "restart") else None)
    _draw_text(p, image, QRectF(52 * sx, 1098 * sy, 376 * sx, 66 * sy), detail, 22 * sx, QColor("#eef7fc"), tracking=2.5 * sx)
    _draw_status_bar(p, sx, sy, left, right)

    if sensor_text:
        _draw_text(p, image, QRectF(85 * sx, 1230 * sy, 310 * sx, 38 * sy), sensor_text, 13 * sx, QColor("#8ca9ba"))
    if clock_text:
        _draw_text(p, image, QRectF(92 * sx, 1300 * sy, 296 * sx, 100 * sy), clock_text, 61 * sx, white, bold=True, glow=glow)
    if date_text:
        _draw_text(p, image, QRectF(100 * sx, 1394 * sy, 280 * sx, 60 * sy), date_text, 25 * sx, QColor("#eef7fc"), tracking=4.0 * sx)

    footer = footer_text or f"OwnDash {__version__}"
    _draw_text(p, image, QRectF(125 * sx, 1605 * sy, 230 * sx, 48 * sy), footer, 14 * sx, QColor("#dcecf5"))
    if animate_ring:
        _draw_animation_sweep(p, sx, sy, animation_phase, left, right)

    p.end()
    return image


def render_system_state_image(width: int, height: int, state: SystemState, theme: str, icon: QIcon, strings: dict[str, str], *, clock_text: str | None = None, date_text: str | None = None, sensor_text: str | None = None, animation_phase: float = 0.0) -> QImage:
    del theme, icon  # Approved artwork already contains the real OwnDash branding.
    width, height = int(width), int(height)
    if state is SystemState.ACTIVE:
        raise ValueError("ACTIVE has no temporary system-state frame")
    if state not in _STATE_KEYS:
        raise ValueError(f"unsupported system state: {state}")

    title, detail = _state_text(state, strings)
    headline, state_detail = _portrait_copy(state, title, detail)
    left, right, symbol, treatment = _STATE_STYLE[state]
    animate = state in (SystemState.LOCKED, SystemState.IDLE)
    phase = float(animation_phase) if animate else 0.0
    return _render_master_family(width, height, headline=headline, detail=state_detail, left_hex=left, right_hex=right, symbol=symbol, treatment=treatment, clock_text=clock_text, date_text=date_text, sensor_text=sensor_text, animation_phase=phase, animate_ring=animate)


def render_disconnected_status_image(width: int, height: int, icon: QIcon, *, status: str = "OwnDash disconnected", detail: str = "No active connection to OwnDash", farewell: str = "See you soon.", theme: str = "owndash", clock_text: str | None = None, date_text: str | None = None) -> QImage:
    del icon, theme
    now = datetime.now()
    headline = str(status or "OwnDash disconnected").upper()
    combined_detail = str(detail or farewell or "")
    if farewell and farewell not in combined_detail:
        combined_detail = f"{combined_detail} · {farewell}" if combined_detail else farewell
    return _render_master_family(int(width), int(height), headline=headline, detail=combined_detail, left_hex="#00eaff", right_hex="#ff35e5", symbol="disconnected", treatment="original", clock_text=clock_text or now.strftime("%H:%M"), date_text=date_text or now.strftime("%d.%m.%Y"), sensor_text=None, animation_phase=0.0, animate_ring=False, footer_text=f"OwnDash {__version__}")
