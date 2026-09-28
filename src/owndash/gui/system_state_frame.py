"""OwnDash system-state renderer using clean lossless state artwork."""
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

_STATE_ASSETS = {
    SystemState.LOCKED: "status_hud_locked.png",
    SystemState.IDLE: "status_hud_idle.png",
    SystemState.SUSPENDING: "status_hud_standby.png",
    # There is no separate approved generic-transition artwork. Mapping this
    # state explicitly to the shutdown design keeps the terminal path honest
    # and deterministic instead of introducing a hidden visual fallback.
    SystemState.TRANSITIONING: "status_hud_shutdown.png",
    SystemState.SHUTTING_DOWN: "status_hud_shutdown.png",
    SystemState.RESTARTING: "status_hud_restart.png",
}
_DISCONNECTED_ASSET = "status_hud_disconnected.png"

_ANIMATION_COLORS = {
    SystemState.LOCKED: (QColor("#00eaff"), QColor("#ff35e5")),
    SystemState.IDLE: (QColor("#00eaff"), QColor("#72ff35")),
}

# The fresh PNG artwork deliberately contains no time, date or version text.
# These reference-space rectangles are reserved exclusively for live overlays.
_CLOCK_PANEL = QRectF(90, 1070, 300, 170)
_CLOCK_RECT = QRectF(100, 1082, 280, 80)
_DATE_RECT = QRectF(100, 1160, 280, 44)
_FOOTER_RECT = QRectF(110, 1435, 260, 36)
_SWEEP_RECT = QRectF(55, 267, 370, 370)


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
    return source.scaled(
        width,
        height,
        Qt.IgnoreAspectRatio,
        Qt.SmoothTransformation,
    ).convertToFormat(QImage.Format_RGB32)


def _scale_rect(rect: QRectF, sx: float, sy: float) -> QRectF:
    return QRectF(
        rect.x() * sx,
        rect.y() * sy,
        rect.width() * sx,
        rect.height() * sy,
    )


def _fit_font(
    image: QImage,
    text: str,
    rect: QRectF,
    pixel_size: float,
    *,
    bold: bool = False,
    tracking: float = 0.0,
) -> QFont:
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


def _draw_centered_text(
    painter: QPainter,
    image: QImage,
    rect: QRectF,
    text: str,
    pixel_size: float,
    *,
    bold: bool = False,
    tracking: float = 0.0,
    color: QColor | None = None,
) -> None:
    if not text:
        return
    painter.save()
    painter.setFont(
        _fit_font(
            image,
            text,
            rect,
            pixel_size,
            bold=bold,
            tracking=tracking,
        )
    )
    painter.setPen(color or QColor("#f7fbff"))
    painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, text)
    painter.restore()


def _paint_runtime_clock(
    image: QImage,
    clock_text: str | None,
    date_text: str | None,
) -> None:
    """Paint live clock/date into the intentionally empty runtime panel."""
    clock = str(clock_text or "").strip()
    date = str(date_text or "").strip()
    if not clock and not date:
        return

    sx = image.width() / _REFERENCE_W
    sy = image.height() / _REFERENCE_H
    panel = _scale_rect(_CLOCK_PANEL, sx, sy)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    gradient = QLinearGradient(
        panel.center().x(),
        panel.top(),
        panel.center().x(),
        panel.bottom(),
    )
    gradient.setColorAt(0.0, QColor(0, 6, 14, 205))
    gradient.setColorAt(0.5, QColor(0, 3, 9, 225))
    gradient.setColorAt(1.0, QColor(0, 7, 15, 205))
    painter.setPen(QPen(QColor(0, 234, 255, 85), max(1.0, 1.0 * sx)))
    painter.setBrush(gradient)
    painter.drawRoundedRect(
        panel,
        20 * sx,
        20 * sy,
    )

    if clock:
        _draw_centered_text(
            painter,
            image,
            _scale_rect(_CLOCK_RECT, sx, sy),
            clock,
            52 * sx,
            bold=True,
        )
    if date:
        _draw_centered_text(
            painter,
            image,
            _scale_rect(_DATE_RECT, sx, sy),
            date,
            19 * sx,
            tracking=1.8 * sx,
            color=QColor("#dcecf4"),
        )
    painter.end()


def _paint_runtime_footer(image: QImage) -> None:
    """Paint the current OwnDash version into the clean footer zone."""
    sx = image.width() / _REFERENCE_W
    sy = image.height() / _REFERENCE_H
    rect = _scale_rect(_FOOTER_RECT, sx, sy)

    painter = QPainter(image)
    painter.fillRect(rect, QColor(0, 4, 10, 135))
    _draw_centered_text(
        painter,
        image,
        rect,
        f"OwnDash {__version__}",
        12 * sx,
        color=QColor("#c8e8f2"),
    )
    painter.end()


def _paint_live_sweep(
    image: QImage,
    state: SystemState,
    animation_phase: float,
) -> None:
    """Draw the only animated element; terminal states remain fully static."""
    phase = float(animation_phase) % 1.0
    if phase == 0.0 or state not in _ANIMATION_COLORS:
        return

    sx = image.width() / _REFERENCE_W
    sy = image.height() / _REFERENCE_H
    left, right = _ANIMATION_COLORS[state]
    rect = _scale_rect(_SWEEP_RECT, sx, sy)
    start = int((90.0 - phase * 360.0) * 16)

    gradient = QLinearGradient(
        rect.left(),
        rect.center().y(),
        rect.right(),
        rect.center().y(),
    )
    gradient.setColorAt(0.0, left)
    gradient.setColorAt(1.0, right)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(
        QPen(
            QColor(255, 255, 255, 55),
            max(5.0, 8 * sx),
            Qt.SolidLine,
            Qt.RoundCap,
        )
    )
    painter.drawArc(rect, start, -22 * 16)
    painter.setPen(
        QPen(
            gradient,
            max(2.0, 3 * sx),
            Qt.SolidLine,
            Qt.RoundCap,
        )
    )
    painter.drawArc(rect, start, -22 * 16)
    painter.end()


def _render_asset(
    width: int,
    height: int,
    filename: str,
    *,
    state: SystemState | None,
    clock_text: str | None,
    date_text: str | None,
    animation_phase: float,
) -> QImage:
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")

    image = _scaled_reference(filename, width, height)
    _paint_runtime_clock(image, clock_text, date_text)
    _paint_runtime_footer(image)
    if state is not None:
        _paint_live_sweep(image, state, animation_phase)
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


def render_disconnected_status_image(
    width: int,
    height: int,
    icon: QIcon,
    *,
    status: str = "OwnDash disconnected",
    detail: str = "No active connection to OwnDash",
    farewell: str = "See you soon.",
    theme: str = "owndash",
    clock_text: str | None = None,
    date_text: str | None = None,
) -> QImage:
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
