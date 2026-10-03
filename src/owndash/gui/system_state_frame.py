"""OwnDash system-state renderer using clean lossless state artwork."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import as_file, files

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QImage, QLinearGradient, QPainter, QPen

from owndash import __version__
from owndash.core.system_state import SystemState
from owndash.gui.system_state_layout import SystemStateLayout, layout_for_content

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

_STATE_ACCENTS = {
    SystemState.LOCKED: (QColor("#00eaff"), QColor("#ff35e5")),
    SystemState.IDLE: (QColor("#00eaff"), QColor("#72ff35")),
    SystemState.SUSPENDING: (QColor("#ffad1f"), QColor("#ffe070")),
    SystemState.TRANSITIONING: (QColor("#ff334f"), QColor("#ff7b45")),
    SystemState.SHUTTING_DOWN: (QColor("#ff334f"), QColor("#ff6b6b")),
    SystemState.RESTARTING: (QColor("#9a5cff"), QColor("#ff35e5")),
}
_DISCONNECTED_ACCENTS = (QColor("#00eaff"), QColor("#ff35e5"))

# The approved 480x1920 PNGs remain the protected physical-reference sheets.
# Their central 370x370 HUD region contains the reusable symbol/ring without
# the generated state wording below it, so responsive layouts can compose that
# visual independently while all mutable text stays runtime-owned.
_HUD_SOURCE_RECT = QRectF(55, 267, 370, 370)

# The approved PNGs contain their state wording as part of the generated source
# artwork. The protected 480x1920 path masks only that central copy block and
# redraws the visible title/detail at runtime so the application language stays
# authoritative.
_STATE_COPY_PANEL = QRectF(50, 730, 380, 255)
_STATE_TITLE_RECT = QRectF(55, 760, 370, 82)
_STATE_DETAIL_RECT = QRectF(55, 842, 370, 48)
_STATE_ACCENT_RECT = QRectF(65, 918, 350, 8)

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
    """Contain the protected 1:4 reference artwork without stretching it."""
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


def _new_font(pixel_size: float, *, bold: bool = False, tracking: float = 0.0) -> QFont:
    font = QFont("DejaVu Sans Condensed")
    font.setBold(bold)
    font.setPixelSize(max(1, round(pixel_size)))
    if tracking:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking)
    return font


def _fit_font(
    image: QImage,
    text: str,
    rect: QRectF,
    pixel_size: float,
    *,
    bold: bool = False,
    tracking: float = 0.0,
) -> QFont:
    font = _new_font(pixel_size, bold=bold, tracking=tracking)
    while font.pixelSize() > 7:
        metrics = QFontMetricsF(font, image)
        if metrics.horizontalAdvance(text) <= rect.width() and metrics.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _fit_detail_text(
    image: QImage,
    text: str,
    rect: QRectF,
    pixel_size: float,
    *,
    tracking: float = 0.0,
) -> tuple[QFont, str]:
    """Fit detail copy into one or two lines without silently dropping words."""
    text = " ".join(str(text or "").split())
    font = _new_font(pixel_size, tracking=tracking)
    if not text:
        return font, ""

    words = text.split()
    minimum = 7
    while font.pixelSize() >= minimum:
        metrics = QFontMetricsF(font, image)
        line_height = metrics.lineSpacing()
        if metrics.horizontalAdvance(text) <= rect.width() and line_height <= rect.height():
            return font, text

        if len(words) > 1 and line_height * 2 <= rect.height():
            candidates: list[tuple[float, str]] = []
            for split in range(1, len(words)):
                first = " ".join(words[:split])
                second = " ".join(words[split:])
                first_width = metrics.horizontalAdvance(first)
                second_width = metrics.horizontalAdvance(second)
                if first_width <= rect.width() and second_width <= rect.width():
                    candidates.append((abs(first_width - second_width), f"{first}\n{second}"))
            if candidates:
                candidates.sort(key=lambda item: item[0])
                return font, candidates[0][1]

        if font.pixelSize() == minimum:
            break
        font.setPixelSize(font.pixelSize() - 1)

    # Extremely narrow targets still keep the complete copy. QPainter clips to
    # the safe detail zone rather than manufacturing or silently dropping text.
    return font, text


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


def _draw_detail_text(
    painter: QPainter,
    image: QImage,
    rect: QRectF,
    text: str,
    pixel_size: float,
    *,
    tracking: float = 0.0,
    color: QColor | None = None,
) -> None:
    if not text:
        return
    font, wrapped = _fit_detail_text(image, text, rect, pixel_size, tracking=tracking)
    painter.save()
    painter.setFont(font)
    painter.setPen(color or QColor("#e6edf2"))
    painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, wrapped)
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
    """Replace only the baked state wording on the protected reference."""
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
    """Paint live clock/date into the protected reference runtime panel."""
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
    """Paint the current OwnDash version into the protected reference footer."""
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
    """Draw the protected-reference animation; terminal states stay static."""
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


def _reference_render(
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
    image, placement = _fitted_reference(filename, width, height)
    _paint_runtime_state_copy(image, placement, title, detail)
    _paint_runtime_clock(image, placement, clock_text, date_text)
    _paint_runtime_footer(image, placement)
    if state is not None:
        _paint_live_sweep(image, placement, state, animation_phase)
    return image


def _state_accents(state: SystemState | None) -> tuple[QColor, QColor]:
    if state is None:
        return _DISCONNECTED_ACCENTS
    return _STATE_ACCENTS[state]


def _responsive_information_panel(layout: SystemStateLayout, has_clock: bool) -> QRectF:
    top = layout.title.top()
    bottom = layout.date.bottom() if has_clock else layout.detail.bottom()
    left = min(layout.title.left(), layout.detail.left(), layout.clock.left(), layout.date.left())
    right = max(layout.title.right(), layout.detail.right(), layout.clock.right(), layout.date.right())
    pad_x = max(4.0, layout.safe.width() * 0.012)
    pad_y = max(4.0, layout.safe.height() * 0.02)
    panel = QRectF(left - pad_x, top - pad_y, (right - left) + pad_x * 2, (bottom - top) + pad_y * 2)
    return panel.intersected(layout.safe)


def _paint_responsive_chrome(
    image: QImage,
    layout: SystemStateLayout,
    accents: tuple[QColor, QColor],
    *,
    has_clock: bool,
) -> None:
    left, right = accents
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    background = QLinearGradient(0.0, 0.0, image.width(), image.height())
    background.setColorAt(0.0, QColor("#020711"))
    background.setColorAt(0.55, QColor("#030b17"))
    background.setColorAt(1.0, QColor("#020711"))
    painter.fillRect(layout.target, background)

    art_gradient = QLinearGradient(layout.art.left(), layout.art.top(), layout.art.right(), layout.art.bottom())
    art_gradient.setColorAt(0.0, QColor(3, 17, 29, 235))
    art_gradient.setColorAt(1.0, QColor(2, 9, 20, 245))
    painter.setPen(QPen(QColor(left.red(), left.green(), left.blue(), 90), 1.5))
    painter.setBrush(art_gradient)
    radius = max(8.0, min(layout.art.width(), layout.art.height()) * 0.045)
    painter.drawRoundedRect(layout.art, radius, radius)

    info = _responsive_information_panel(layout, has_clock)
    info_gradient = QLinearGradient(info.left(), info.top(), info.right(), info.bottom())
    info_gradient.setColorAt(0.0, QColor(2, 12, 22, 238))
    info_gradient.setColorAt(1.0, QColor(5, 8, 19, 244))
    painter.setPen(QPen(QColor(right.red(), right.green(), right.blue(), 75), 1.25))
    painter.setBrush(info_gradient)
    painter.drawRoundedRect(info, max(8.0, info.height() * 0.04), max(8.0, info.height() * 0.04))

    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(left.red(), left.green(), left.blue(), 45), 1.0))
    painter.drawRoundedRect(layout.safe, max(6.0, layout.safe.height() * 0.015), max(6.0, layout.safe.height() * 0.015))
    painter.end()


def _responsive_art(filename: str) -> QImage:
    source = _reference_image(filename)
    return source.copy(
        round(_HUD_SOURCE_RECT.x()),
        round(_HUD_SOURCE_RECT.y()),
        round(_HUD_SOURCE_RECT.width()),
        round(_HUD_SOURCE_RECT.height()),
    )


def _paint_responsive_art(image: QImage, layout: SystemStateLayout, filename: str) -> None:
    source = _responsive_art(filename)
    max_w = max(1, round(layout.art.width() * 0.90))
    max_h = max(1, round(layout.art.height() * 0.90))
    scaled = source.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    x = layout.art.center().x() - scaled.width() / 2.0
    y = layout.art.center().y() - scaled.height() / 2.0

    painter = QPainter(image)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage(round(x), round(y), scaled)
    painter.end()


def _responsive_base_size(image: QImage) -> float:
    return float(max(1, min(image.width(), image.height())))


def _paint_responsive_state_copy(
    image: QImage,
    layout: SystemStateLayout,
    title: str,
    detail: str,
    accents: tuple[QColor, QColor],
) -> None:
    base = _responsive_base_size(image)
    left, right = accents
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    _draw_centered_text(
        painter,
        image,
        layout.title,
        title,
        min(layout.title.height() * 0.66, base * 0.095),
        bold=True,
        tracking=max(0.0, min(3.0, base * 0.0025)),
    )
    _draw_detail_text(
        painter,
        image,
        layout.detail,
        detail,
        min(layout.detail.height() * 0.42, base * 0.043),
        tracking=max(0.0, min(1.2, base * 0.0012)),
        color=QColor("#e6edf2"),
    )

    line_y = layout.accent.center().y()
    accent_gradient = QLinearGradient(layout.accent.left(), line_y, layout.accent.right(), line_y)
    accent_gradient.setColorAt(0.0, left)
    accent_gradient.setColorAt(1.0, right)
    painter.setPen(
        QPen(
            accent_gradient,
            max(1.0, min(5.0, layout.accent.height() * 0.45)),
            Qt.SolidLine,
            Qt.RoundCap,
        )
    )
    painter.drawLine(layout.accent.left(), line_y, layout.accent.right(), line_y)
    painter.end()


def _paint_responsive_clock(
    image: QImage,
    layout: SystemStateLayout,
    clock_text: str | None,
    date_text: str | None,
) -> None:
    clock = str(clock_text or "").strip()
    date = str(date_text or "").strip()
    if not clock and not date:
        return

    base = _responsive_base_size(image)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    if clock:
        _draw_centered_text(
            painter,
            image,
            layout.clock,
            clock,
            min(layout.clock.height() * 0.72, base * 0.105),
            bold=True,
        )
    if date:
        _draw_centered_text(
            painter,
            image,
            layout.date,
            date,
            min(layout.date.height() * 0.60, base * 0.042),
            tracking=max(0.0, min(1.5, base * 0.0015)),
            color=QColor("#dcecf4"),
        )
    painter.end()


def _paint_responsive_footer(image: QImage, layout: SystemStateLayout) -> None:
    painter = QPainter(image)
    painter.fillRect(layout.footer, QColor(0, 4, 10, 145))
    _draw_centered_text(
        painter,
        image,
        layout.footer,
        f"OwnDash {__version__}",
        min(layout.footer.height() * 0.58, _responsive_base_size(image) * 0.025),
        color=QColor("#c8e8f2"),
    )
    painter.end()


def _paint_responsive_sweep(
    image: QImage,
    layout: SystemStateLayout,
    state: SystemState,
    animation_phase: float,
) -> None:
    phase = float(animation_phase) % 1.0
    if phase == 0.0 or state not in _ANIMATION_COLORS:
        return

    side = min(layout.art.width(), layout.art.height()) * 0.78
    rect = QRectF(
        layout.art.center().x() - side / 2.0,
        layout.art.center().y() - side / 2.0,
        side,
        side,
    )
    left, right = _ANIMATION_COLORS[state]
    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, left)
    gradient.setColorAt(1.0, right)
    start = int((90.0 - phase * 360.0) * 16)
    width = max(1.0, min(6.0, side * 0.012))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(255, 255, 255, 55), width * 2.2, Qt.SolidLine, Qt.RoundCap))
    painter.drawArc(rect, start, -22 * 16)
    painter.setPen(QPen(gradient, width, Qt.SolidLine, Qt.RoundCap))
    painter.drawArc(rect, start, -22 * 16)
    painter.end()


def _responsive_render(
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
    has_clock = bool(str(clock_text or "").strip() or str(date_text or "").strip())
    has_detail = bool(str(detail or "").strip())
    layout = layout_for_content(
        width,
        height,
        has_clock=has_clock,
        has_detail=has_detail,
    )
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(_CANVAS_BACKGROUND)
    accents = _state_accents(state)

    _paint_responsive_chrome(image, layout, accents, has_clock=has_clock)
    _paint_responsive_art(image, layout, filename)
    _paint_responsive_state_copy(image, layout, title, detail, accents)
    _paint_responsive_clock(image, layout, clock_text, date_text)
    _paint_responsive_footer(image, layout)
    if state is not None:
        _paint_responsive_sweep(image, layout, state, animation_phase)
    return image


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

    if (width, height) == (_REFERENCE_W, _REFERENCE_H):
        return _reference_render(
            width,
            height,
            filename,
            state=state,
            title=title,
            detail=detail,
            clock_text=clock_text,
            date_text=date_text,
            animation_phase=animation_phase,
        )

    return _responsive_render(
        width,
        height,
        filename,
        state=state,
        title=title,
        detail=detail,
        clock_text=clock_text,
        date_text=date_text,
        animation_phase=animation_phase,
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
    if state is SystemState.IDLE:
        date_text = None
    elif state not in _ANIMATION_COLORS:
        clock_text = None
        date_text = None
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
    del icon, farewell, theme, clock_text, date_text
    return _render_asset(
        width,
        height,
        _DISCONNECTED_ASSET,
        state=None,
        title=_headline_for_state(None, str(status or "OwnDash disconnected")),
        detail=str(detail or ""),
        clock_text=None,
        date_text=None,
        animation_phase=0.0,
    )
