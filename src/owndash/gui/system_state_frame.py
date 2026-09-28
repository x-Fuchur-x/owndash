"""OwnDash system-state renderer using clean lossless state artwork."""
from __future__ import annotations

from dataclasses import dataclass
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
_CANVAS_BACKGROUND = QColor("#020711")

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

_STATE_COPY_KEYS = {
    SystemState.LOCKED: ("system_locked", None),
    SystemState.IDLE: ("idle", None),
    SystemState.SUSPENDING: ("standby", "entering_standby"),
    SystemState.TRANSITIONING: ("system_transition", "ending_session"),
    SystemState.SHUTTING_DOWN: ("shutting_down", None),
    SystemState.RESTARTING: ("restarting", None),
}

_ANIMATION_COLORS = {
    SystemState.LOCKED: (QColor("#00eaff"), QColor("#ff35e5")),
    SystemState.IDLE: (QColor("#00eaff"), QColor("#72ff35")),
}

# The approved PNGs contain their state wording as part of the generated source
# artwork. OwnDash masks only that central copy block and redraws the visible
# title/detail at runtime so the application language remains authoritative.
_STATE_COPY_PANEL = QRectF(55, 730, 370, 255)
_STATE_TITLE_RECT = QRectF(65, 760, 350, 82)
_STATE_DETAIL_RECT = QRectF(72, 842, 336, 48)
_STATE_ACCENT_RECT = QRectF(75, 918, 330, 8)

# The fresh PNG artwork deliberately contains no time, date or version text.
# These reference-space rectangles are reserved exclusively for live overlays.
_CLOCK_PANEL = QRectF(90, 1070, 300, 170)
_CLOCK_RECT = QRectF(100, 1082, 280, 80)
_DATE_RECT = QRectF(100, 1160, 280, 44)
_FOOTER_RECT = QRectF(110, 1435, 260, 36)
_SWEEP_RECT = QRectF(55, 267, 370, 370)


@dataclass(frozen=True, slots=True)
class _Placement:
    x: float
    y: float
    sx: float
    sy: float

    @property
    def pen_scale(self) -> float:
        return max(0.01, min(self.sx, self.sy))


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


def _fitted_reference(filename: str, width: int, height: int) -> tuple[QImage, _Placement]:
    """Contain the 1:4 artwork without ever stretching its geometry."""
    source = _reference_image(filename)
    if (width, height) == (_REFERENCE_W, _REFERENCE_H):
        return source.copy(), _Placement(0.0, 0.0, 1.0, 1.0)

    scale = min(width / _REFERENCE_W, height / _REFERENCE_H)
    target_w = max(1, min(width, round(_REFERENCE_W * scale)))
    target_h = max(1, min(height, round(_REFERENCE_H * scale)))
    scaled = source.scaled(
        target_w,
        target_h,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    ).convertToFormat(QImage.Format_RGB32)

    canvas = QImage(width, height, QImage.Format_RGB32)
    canvas.fill(_CANVAS_BACKGROUND)
    x = (width - scaled.width()) / 2.0
    y = (height - scaled.height()) / 2.0
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage(round(x), round(y), scaled)
    painter.end()

    return canvas, _Placement(
        x,
        y,
        scaled.width() / _REFERENCE_W,
        scaled.height() / _REFERENCE_H,
    )


def _map_rect(rect: QRectF, placement: _Placement) -> QRectF:
    return QRectF(
        placement.x + rect.x() * placement.sx,
        placement.y + rect.y() * placement.sy,
        rect.width() * placement.sx,
        rect.height() * placement.sy,
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


def _headline_for_state(state: SystemState | None, title: str) -> str:
    title = title.strip()
    if state is SystemState.LOCKED:
        lowered = title.lower()
        if lowered.startswith("system "):
            title = title[7:].strip()
    return title.upper()


def _state_copy(state: SystemState, strings: dict[str, str]) -> tuple[str, str]:
    title_key, detail_key = _STATE_COPY_KEYS[state]
    title = str(strings.get(title_key) or title_key.replace("_", " ")).strip()
    detail = str(strings.get(detail_key) or "").strip() if detail_key else ""
    if state is SystemState.LOCKED and not detail:
        detail = title
    return _headline_for_state(state, title), detail


def _paint_runtime_state_copy(
    image: QImage,
    placement: _Placement,
    title: str,
    detail: str,
) -> None:
    """Replace only the baked state wording with localized runtime copy."""
    panel = _map_rect(_STATE_COPY_PANEL, placement)
    title_rect = _map_rect(_STATE_TITLE_RECT, placement)
    detail_rect = _map_rect(_STATE_DETAIL_RECT, placement)
    accent_rect = _map_rect(_STATE_ACCENT_RECT, placement)
    scale = placement.pen_scale

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    background = QLinearGradient(
        panel.center().x(),
        panel.top(),
        panel.center().x(),
        panel.bottom(),
    )
    background.setColorAt(0.0, QColor("#03111d"))
    background.setColorAt(0.45, QColor("#020c16"))
    background.setColorAt(1.0, QColor("#020914"))
    painter.fillRect(panel, background)

    _draw_centered_text(
        painter,
        image,
        title_rect,
        title,
        46 * scale,
        bold=True,
        tracking=4.0 * scale,
    )
    _draw_centered_text(
        painter,
        image,
        detail_rect,
        detail,
        20 * scale,
        tracking=1.4 * scale,
        color=QColor("#e6edf2"),
    )

    line_y = accent_rect.center().y()
    gradient = QLinearGradient(accent_rect.left(), line_y, accent_rect.right(), line_y)
    gradient.setColorAt(0.0, QColor("#00eaff"))
    gradient.setColorAt(0.5, QColor("#42e7ff"))
    gradient.setColorAt(1.0, QColor("#ff35e5"))
    painter.setPen(QPen(gradient, max(1.0, 4.0 * scale), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(accent_rect.left(), line_y, accent_rect.right(), line_y)
    painter.end()


def _paint_runtime_clock(
    image: QImage,
    placement: _Placement,
    clock_text: str | None,
    date_text: str | None,
) -> None:
    """Paint live clock/date into the intentionally empty runtime panel."""
    clock = str(clock_text or "").strip()
    date = str(date_text or "").strip()
    if not clock and not date:
        return

    panel = _map_rect(_CLOCK_PANEL, placement)
    scale = placement.pen_scale

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
    painter.setPen(QPen(QColor(0, 234, 255, 85), max(1.0, 1.0 * scale)))
    painter.setBrush(gradient)
    painter.drawRoundedRect(panel, 20 * scale, 20 * scale)

    if clock:
        _draw_centered_text(
            painter,
            image,
            _map_rect(_CLOCK_RECT, placement),
            clock,
            52 * scale,
            bold=True,
        )
    if date:
        _draw_centered_text(
            painter,
            image,
            _map_rect(_DATE_RECT, placement),
            date,
            19 * scale,
            tracking=1.8 * scale,
            color=QColor("#dcecf4"),
        )
    painter.end()


def _paint_runtime_footer(image: QImage, placement: _Placement) -> None:
    """Paint the current OwnDash version into the clean footer zone."""
    rect = _map_rect(_FOOTER_RECT, placement)
    scale = placement.pen_scale

    painter = QPainter(image)
    painter.fillRect(rect, QColor(0, 4, 10, 135))
    _draw_centered_text(
        painter,
        image,
        rect,
        f"OwnDash {__version__}",
        12 * scale,
        color=QColor("#c8e8f2"),
    )
    painter.end()


def _paint_live_sweep(
    image: QImage,
    placement: _Placement,
    state: SystemState,
    animation_phase: float,
) -> None:
    """Draw the only animated element; terminal states remain fully static."""
    phase = float(animation_phase) % 1.0
    if phase == 0.0 or state not in _ANIMATION_COLORS:
        return

    left, right = _ANIMATION_COLORS[state]
    rect = _map_rect(_SWEEP_RECT, placement)
    scale = placement.pen_scale
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
            max(1.0, 8 * scale),
            Qt.SolidLine,
            Qt.RoundCap,
        )
    )
    painter.drawArc(rect, start, -22 * 16)
    painter.setPen(
        QPen(
            gradient,
            max(1.0, 3 * scale),
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
    title: str,
    detail: str,
    clock_text: str | None,
    date_text: str | None,
    animation_phase: float,
) -> QImage:
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")

    image, placement = _fitted_reference(filename, width, height)
    _paint_runtime_state_copy(image, placement, title, detail)
    _paint_runtime_clock(image, placement, clock_text, date_text)
    _paint_runtime_footer(image, placement)
    if state is not None:
        _paint_live_sweep(image, placement, state, animation_phase)
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
    # Theme/icon/context parameters stay in the public API for compatibility.
    # The approved artwork is one theme-independent family and is never recolored.
    del theme, icon, sensor_text
    if state is SystemState.ACTIVE:
        raise ValueError("ACTIVE has no temporary system-state frame")
    try:
        filename = _STATE_ASSETS[state]
        title, detail = _state_copy(state, strings)
    except KeyError as exc:
        raise ValueError(f"unsupported system state: {state}") from exc
    phase = float(animation_phase) if state in _ANIMATION_COLORS else 0.0
    return _render_asset(
        width,
        height,
        filename,
        state=state,
        title=title,
        detail=detail,
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
    del icon, farewell, theme
    now = datetime.now()
    return _render_asset(
        width,
        height,
        _DISCONNECTED_ASSET,
        state=None,
        title=_headline_for_state(None, str(status or "OwnDash disconnected")),
        detail=str(detail or ""),
        clock_text=clock_text or now.strftime("%H:%M"),
        date_text=date_text or now.strftime("%d.%m.%Y"),
        animation_phase=0.0,
    )
