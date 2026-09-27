"""Single-path OwnDash system-state renderer using the approved state artwork."""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from importlib.resources import as_file, files

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QImage, QLinearGradient, QPainter, QPen

from owndash import __version__
from owndash.core.system_state import SystemState

_REFERENCE_W = 480
_REFERENCE_H = 1920
_REFERENCE_CLOCK = "18:35"
_REFERENCE_DATE = "27.09.2026"
_REFERENCE_FOOTER = "OwnDash 0.14.0 Beta 4"

_STATE_ASSETS = {
    SystemState.LOCKED: "status_hud_locked.jpg",
    SystemState.IDLE: "status_hud_idle.jpg",
    SystemState.SUSPENDING: "status_hud_standby.jpg",
    # There is no separate approved generic-transition artwork. Mapping this
    # state explicitly to the shutdown design keeps the terminal path honest
    # and deterministic instead of introducing a hidden visual fallback.
    SystemState.TRANSITIONING: "status_hud_shutdown.jpg",
    SystemState.SHUTTING_DOWN: "status_hud_shutdown.jpg",
    SystemState.RESTARTING: "status_hud_restart.jpg",
}
_DISCONNECTED_ASSET = "status_hud_disconnected.jpg"

_ANIMATION_COLORS = {
    SystemState.LOCKED: (QColor("#00eaff"), QColor("#ff35e5")),
    SystemState.IDLE: (QColor("#00eaff"), QColor("#72ff35")),
}


def _resource(filename: str):
    return files("owndash").joinpath("assets", filename)


@lru_cache(maxsize=8)
def _reference_image(filename: str) -> QImage:
    """Decode through Pillow so reference-test and production RGB agree."""
    with as_file(_resource(filename)) as path:
        with Image.open(path) as source:
            rgb = source.convert("RGB")
            data = rgb.tobytes("raw", "RGB")
            image = QImage(
                data,
                rgb.width,
                rgb.height,
                rgb.width * 3,
                QImage.Format_RGB888,
            ).copy()
    return image.convertToFormat(QImage.Format_RGB32)


def _scaled_reference(filename: str, width: int, height: int) -> QImage:
    source = _reference_image(filename)
    if (width, height) == (_REFERENCE_W, _REFERENCE_H):
        return source.copy()
    return source.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_RGB32)


def _fit_font(image: QImage, text: str, rect: QRectF, pixel_size: float, *, bold: bool = False, tracking: float = 0.0) -> QFont:
    font = QFont("DejaVu Sans Condensed")
    font.setBold(bold)
    font.setPixelSize(max(1, round(pixel_size)))
    if tracking:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking)
    while font.pixelSize() > 7:
        metrics = QFontMetricsF(font, image)
        if metrics.horizontalAdvance(text) <= rect.width() and metrics.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _draw_centered_text(painter: QPainter, image: QImage, rect: QRectF, text: str, pixel_size: float, *, bold: bool = False, tracking: float = 0.0) -> None:
    if not text:
        return
    painter.save()
    painter.setFont(_fit_font(image, text, rect, pixel_size, bold=bold, tracking=tracking))
    painter.setPen(QColor("#f7fbff"))
    painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, text)
    painter.restore()


def _paint_runtime_clock(image: QImage, clock_text: str | None, date_text: str | None) -> None:
    """Replace only the baked demo clock/date when live values differ."""
    clock = str(clock_text or "")
    date = str(date_text or "")
    if (not clock or clock == _REFERENCE_CLOCK) and (not date or date == _REFERENCE_DATE):
        return

    sx = image.width() / _REFERENCE_W
    sy = image.height() / _REFERENCE_H
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    patch = QRectF(72 * sx, 1280 * sy, 336 * sx, 190 * sy)
    gradient = QLinearGradient(patch.center().x(), patch.top(), patch.center().x(), patch.bottom())
    gradient.setColorAt(0.0, QColor(0, 4, 10, 238))
    gradient.setColorAt(0.5, QColor(0, 3, 8, 252))
    gradient.setColorAt(1.0, QColor(0, 5, 11, 238))
    painter.fillRect(patch, gradient)

    if clock:
        _draw_centered_text(
            painter,
            image,
            QRectF(82 * sx, 1300 * sy, 316 * sx, 105 * sy),
            clock,
            61 * sx,
            bold=True,
        )
    if date:
        _draw_centered_text(
            painter,
            image,
            QRectF(84 * sx, 1392 * sy, 312 * sx, 60 * sy),
            date,
            25 * sx,
            tracking=3.0 * sx,
        )
    painter.end()


def _paint_runtime_footer(image: QImage) -> None:
    footer = f"OwnDash {__version__}"
    if footer == _REFERENCE_FOOTER:
        return
    sx = image.width() / _REFERENCE_W
    sy = image.height() / _REFERENCE_H
    painter = QPainter(image)
    patch = QRectF(118 * sx, 1590 * sy, 244 * sx, 80 * sy)
    painter.fillRect(patch, QColor(0, 5, 11, 235))
    _draw_centered_text(painter, image, patch, footer, 13 * sx)
    painter.end()


def _paint_live_sweep(image: QImage, state: SystemState, animation_phase: float) -> None:
    """Draw the only animated element; phase zero is the untouched reference."""
    phase = float(animation_phase) % 1.0
    if phase == 0.0 or state not in _ANIMATION_COLORS:
        return
    sx = image.width() / _REFERENCE_W
    sy = image.height() / _REFERENCE_H
    left, right = _ANIMATION_COLORS[state]
    rect = QRectF(42 * sx, 323 * sy, 396 * sx, 620 * sy)
    start = int((90.0 - phase * 360.0) * 16)
    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, left)
    gradient.setColorAt(1.0, right)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 55), max(6.0, 10 * sx), Qt.SolidLine, Qt.RoundCap))
    painter.drawArc(rect, start, -24 * 16)
    painter.setPen(QPen(gradient, max(2.0, 3 * sx), Qt.SolidLine, Qt.RoundCap))
    painter.drawArc(rect, start, -24 * 16)
    painter.end()


def _render_asset(width: int, height: int, filename: str, *, state: SystemState | None, clock_text: str | None, date_text: str | None, animation_phase: float) -> QImage:
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")
    image = _scaled_reference(filename, width, height)
    _paint_runtime_clock(image, clock_text, date_text)
    _paint_runtime_footer(image)
    if state is not None:
        _paint_live_sweep(image, state, animation_phase)
    return image


def render_system_state_image(width: int, height: int, state: SystemState, theme: str, icon: QIcon, strings: dict[str, str], *, clock_text: str | None = None, date_text: str | None = None, sensor_text: str | None = None, animation_phase: float = 0.0) -> QImage:
    # Theme/copy/icon/context parameters stay in the public API for compatibility.
    # The approved state artwork itself is theme-independent and is never recolored.
    del theme, icon, strings, sensor_text
    if state is SystemState.ACTIVE:
        raise ValueError("ACTIVE has no temporary system-state frame")
    try:
        filename = _STATE_ASSETS[state]
    except KeyError as exc:
        raise ValueError(f"unsupported system state: {state}") from exc
    phase = float(animation_phase) if state in _ANIMATION_COLORS else 0.0
    return _render_asset(
        width,
        height,
        filename,
        state=state,
        clock_text=clock_text,
        date_text=date_text,
        animation_phase=phase,
    )


def render_disconnected_status_image(width: int, height: int, icon: QIcon, *, status: str = "OwnDash disconnected", detail: str = "No active connection to OwnDash", farewell: str = "See you soon.", theme: str = "owndash", clock_text: str | None = None, date_text: str | None = None) -> QImage:
    del icon, status, detail, farewell, theme
    now = datetime.now()
    return _render_asset(
        width,
        height,
        _DISCONNECTED_ASSET,
        state=None,
        clock_text=clock_text or now.strftime("%H:%M"),
        date_text=date_text or now.strftime("%d.%m.%Y"),
        animation_phase=0.0,
    )
