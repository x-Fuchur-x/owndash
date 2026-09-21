"""Resolution-independent neon HUD screens for Linux system states."""
from __future__ import annotations

from dataclasses import dataclass
import math

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
    QPainterPath,
    QPen,
    QRadialGradient,
)

from owndash import APP_NAME, __version__
from owndash.core.system_state import SystemState


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
    rail: str


@dataclass(frozen=True, slots=True)
class _PortraitLayout:
    """Reference-scale geometry for the narrow 480×1920 class of displays."""

    hud_center: QPointF
    hud_diameter: float
    brand_icon_rect: QRectF
    wordmark_rect: QRectF
    wordmark_font_px: float
    status_panel_rect: QRectF
    status_icon_rect: QRectF
    status_rect: QRectF
    status_font_px: float
    detail_rect: QRectF
    detail_font_px: float
    bar_rect: QRectF
    progress_label_rect: QRectF
    context_top: float
    floor_horizon: float


_THEMES = {
    "owndash": _Theme(
        top="#06141f",
        middle="#020811",
        bottom="#010307",
        primary="#f7fcff",
        secondary="#b8d5e6",
        muted="#61798a",
        cyan="#00e7ff",
        green="#5af59a",
        magenta="#ff2aae",
        rail="#37dcff",
    ),
    "bazzite-inspired": _Theme(
        top="#10142a",
        middle="#070919",
        bottom="#02040d",
        primary="#f8f6ff",
        secondary="#cbc8ff",
        muted="#8581a8",
        cyan="#55d9ff",
        green="#8d7cff",
        magenta="#d95cff",
        rail="#6f8dff",
    ),
}

_STATE_ACCENTS = {
    SystemState.IDLE: "#50f38a",
    SystemState.LOCKED: "#00e5ff",
    SystemState.SUSPENDING: "#63d8ff",
    SystemState.TRANSITIONING: "#78cfff",
    SystemState.SHUTTING_DOWN: "#ff9c62",
    SystemState.RESTARTING: "#cf7cff",
}

_STATE_KEYS = {
    SystemState.IDLE: ("idle", ""),
    SystemState.LOCKED: ("system_locked", ""),
    SystemState.SUSPENDING: ("standby", "entering_standby"),
    SystemState.TRANSITIONING: ("system_transition", "ending_session"),
    SystemState.SHUTTING_DOWN: ("shutting_down", ""),
    SystemState.RESTARTING: ("restarting", ""),
}

_ANIMATED_STATES = {SystemState.IDLE, SystemState.LOCKED}


def _portrait_layout(width: int, height: int) -> _PortraitLayout:
    """Return the approved v9 portrait composition for narrow case displays."""
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("portrait layout dimensions must be positive")

    # v9 is intentionally zoned: brand HUD, system state, then clock/context.
    # The OwnDash wordmark stays inside the clear center of the ring while the
    # status area has generous fixed side margins for long localized labels.
    center = QPointF(width * 0.50, height * 0.205)
    diameter = width * 0.76
    icon_side = width * 0.22
    icon_center = QPointF(center.x(), center.y() - diameter * 0.105)
    brand_icon_rect = QRectF(
        icon_center.x() - icon_side / 2.0,
        icon_center.y() - icon_side / 2.0,
        icon_side,
        icon_side,
    )
    status_panel = QRectF(width * 0.08, height * 0.455, width * 0.84, height * 0.205)
    state_icon_side = width * 0.115
    return _PortraitLayout(
        hud_center=center,
        hud_diameter=diameter,
        brand_icon_rect=brand_icon_rect,
        wordmark_rect=QRectF(width * 0.18, center.y() + diameter * 0.095, width * 0.64, height * 0.048),
        wordmark_font_px=width * 0.125,
        status_panel_rect=status_panel,
        status_icon_rect=QRectF(
            width * 0.50 - state_icon_side / 2.0,
            height * 0.475,
            state_icon_side,
            state_icon_side,
        ),
        status_rect=QRectF(width * 0.08, height * 0.525, width * 0.84, height * 0.060),
        status_font_px=width * 0.160,
        detail_rect=QRectF(width * 0.12, height * 0.590, width * 0.76, height * 0.036),
        detail_font_px=width * 0.035,
        bar_rect=QRectF(width * 0.21, height * 0.632, width * 0.58, max(8.0, width * 0.018)),
        progress_label_rect=QRectF(width * 0.18, height * 0.642, width * 0.64, height * 0.025),
        context_top=height * 0.720,
        floor_horizon=height * 0.900,
    )

def _portrait_brand_icon_rect(layout: _PortraitLayout) -> QRectF:
    """Return the app-mark area reserved above the OwnDash wordmark."""
    return QRectF(layout.brand_icon_rect)


def _point_on_circle(center: QPointF, radius: float, degrees: float) -> QPointF:
    angle = math.radians(degrees)
    return QPointF(center.x() + math.cos(angle) * radius, center.y() + math.sin(angle) * radius)


def _portrait_rail_docks(layout: _PortraitLayout) -> tuple[QPointF, QPointF, QPointF, QPointF]:
    """Return rail-to-HUD junctions in visual order."""
    radius = layout.hud_diameter / 2.0
    return (
        _point_on_circle(layout.hud_center, radius, 215.0),
        _point_on_circle(layout.hud_center, radius, 145.0),
        _point_on_circle(layout.hud_center, radius, 325.0),
        _point_on_circle(layout.hud_center, radius, 35.0),
    )


def _portrait_rail_approaches(layout: _PortraitLayout) -> tuple[QPointF, QPointF, QPointF, QPointF]:
    """Return approach points whose final segment is tangent to the hero ring.

    This makes the side rails read as one continuous engineered assembly with
    the circle instead of as unrelated vertical lines crossing the HUD.
    """
    docks = _portrait_rail_docks(layout)
    angles = (215.0, 145.0, 325.0, 35.0)
    signs = (1.0, -1.0, -1.0, 1.0)
    length = layout.hud_diameter * 0.085
    approaches: list[QPointF] = []
    for dock, degrees, sign in zip(docks, angles, signs):
        angle = math.radians(degrees)
        tangent_x = -math.sin(angle) * sign
        tangent_y = math.cos(angle) * sign
        approaches.append(
            QPointF(
                dock.x() - tangent_x * length,
                dock.y() - tangent_y * length,
            )
        )
    return tuple(approaches)  # type: ignore[return-value]


def _text(strings: dict[str, str], key: str, fallback: str) -> str:
    value = strings.get(key)
    return str(value) if value else fallback


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
    title = _text(strings, title_key, defaults[title_key])
    detail = _text(strings, detail_key, defaults[detail_key]) if detail_key else ""
    return title, detail


def _fit_font(image: QImage, text: str, rect: QRectF, px: float, *, bold: bool = False, family: str = "DejaVu Sans") -> QFont:
    font = QFont(family)
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
    glow: str | None = None,
    family: str = "DejaVu Sans",
) -> None:
    if not text:
        return
    font = _fit_font(image, text, rect, px, bold=bold, family=family)
    painter.setFont(font)
    flags = Qt.AlignCenter | Qt.TextWordWrap
    if glow:
        glow_color = QColor(glow)
        for dx, dy, alpha in (
            (-2, 0, 22),
            (2, 0, 22),
            (0, -2, 22),
            (0, 2, 22),
            (-1, 0, 58),
            (1, 0, 58),
            (0, -1, 58),
            (0, 1, 58),
        ):
            glow_color.setAlpha(alpha)
            painter.setPen(glow_color)
            painter.drawText(rect.translated(dx, dy), flags, text)
    painter.setPen(QColor(color))
    painter.drawText(rect, flags, text)


def _fit_single_line_font(
    image: QImage,
    text: str,
    rect: QRectF,
    px: float,
    *,
    bold: bool = False,
    family: str = "DejaVu Sans",
) -> QFont:
    font = QFont(family)
    font.setBold(bold)
    font.setPixelSize(max(1, round(px)))
    while font.pixelSize() > 8:
        metrics = QFontMetricsF(font, image)
        if metrics.horizontalAdvance(text) <= rect.width() and metrics.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _draw_centered_single_line(
    painter: QPainter,
    image: QImage,
    rect: QRectF,
    text: str,
    px: float,
    color: str,
    *,
    bold: bool = False,
    glow: str | None = None,
    family: str = "DejaVu Sans",
) -> None:
    if not text:
        return
    font = _fit_single_line_font(image, text, rect, px, bold=bold, family=family)
    painter.setFont(font)
    flags = Qt.AlignCenter | Qt.AlignVCenter
    if glow:
        glow_color = QColor(glow)
        for dx, dy, alpha in ((-2, 0, 18), (2, 0, 18), (0, -2, 18), (0, 2, 18), (-1, 0, 54), (1, 0, 54)):
            glow_color.setAlpha(alpha)
            painter.setPen(glow_color)
            painter.drawText(rect.translated(dx, dy), flags, text)
    painter.setPen(QColor(color))
    painter.drawText(rect, flags, text)


def _draw_gradient_wordmark(painter: QPainter, image: QImage, rect: QRectF, palette: _Theme, px: float) -> None:
    """Draw a crisp OwnDash hero mark with controlled neon bloom."""
    font = _fit_font(image, APP_NAME, rect, px, bold=True, family="DejaVu Sans Condensed")
    metrics = QFontMetricsF(font, image)
    bounds = metrics.boundingRect(APP_NAME)
    baseline_x = rect.center().x() - bounds.width() / 2.0 - bounds.left()
    baseline_y = rect.center().y() + (metrics.ascent() - metrics.descent()) / 2.0
    path = QPainterPath()
    path.addText(QPointF(baseline_x, baseline_y), font, APP_NAME)

    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, QColor(palette.cyan))
    gradient.setColorAt(0.49, QColor(palette.green))
    gradient.setColorAt(1.0, QColor(palette.magenta))

    painter.save()
    painter.setBrush(Qt.NoBrush)
    for stroke_width, opacity in ((10.0, 0.09), (5.0, 0.20), (2.5, 0.34)):
        painter.setOpacity(opacity)
        painter.setPen(QPen(QBrush(gradient), stroke_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

    painter.setOpacity(1.0)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawPath(path)

    core = QColor("#f8fdff")
    core.setAlpha(220)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(core, 1.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(path)
    painter.restore()


def _draw_brand_icon(
    painter: QPainter,
    icon: QIcon,
    rect: QRectF,
    short: float,
    palette: _Theme,
) -> None:
    """Render the real OwnDash app mark as a small illuminated badge."""
    if icon.isNull():
        return

    center = rect.center()
    halo = QRadialGradient(center, rect.width() * 0.82)
    core = QColor(palette.cyan)
    core.setAlpha(82)
    edge = QColor(palette.magenta)
    edge.setAlpha(0)
    halo.setColorAt(0.0, core)
    halo.setColorAt(0.58, QColor(10, 28, 40, 72))
    halo.setColorAt(1.0, edge)

    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(halo)
    halo_rect = rect.adjusted(-short * 0.024, -short * 0.024, short * 0.024, short * 0.024)
    painter.drawEllipse(halo_rect)

    rim = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
    rim.setColorAt(0.0, QColor(palette.cyan))
    rim.setColorAt(0.52, QColor(palette.green))
    rim.setColorAt(1.0, QColor(palette.magenta))
    painter.setBrush(QColor(3, 10, 18, 218))
    painter.setPen(QPen(QBrush(rim), max(1.0, short * 0.004), Qt.SolidLine))
    painter.drawRoundedRect(rect, rect.width() * 0.22, rect.width() * 0.22)

    side = max(1, round(rect.width() * 0.84))
    pixmap = icon.pixmap(side, side)
    target = QRectF(
        center.x() - side / 2.0,
        center.y() - side / 2.0,
        side,
        side,
    )
    painter.drawPixmap(target.toRect(), pixmap)
    painter.restore()


def _neon_color_for_angle(palette: _Theme, degrees: float) -> QColor:
    normalized = degrees % 360.0
    if 62.0 <= normalized < 118.0:
        return QColor(palette.green)
    if 118.0 <= normalized < 270.0:
        return QColor(palette.cyan)
    return QColor(palette.magenta)


def _draw_segmented_ring(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    *,
    segments: int,
    coverage: float,
    width_scale: float,
    phase_degrees: float,
    alpha: int,
) -> None:
    ring = QRectF(center.x() - diameter / 2.0, center.y() - diameter / 2.0, diameter, diameter)
    step = 360.0 / float(segments)
    span = step * coverage
    for index in range(segments):
        start = index * step + phase_degrees
        color = _neon_color_for_angle(palette, start + span / 2.0)
        halo = QColor(color)
        halo.setAlpha(max(8, int(alpha * 0.11)))
        painter.setPen(QPen(halo, max(3.0, short * width_scale * 3.6), Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, int(start * 16), int(span * 16))
        color.setAlpha(alpha)
        painter.setPen(QPen(color, max(1.2, short * width_scale), Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, int(start * 16), int(span * 16))


def _draw_hud_rings(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    state: SystemState,
    phase: float,
) -> None:
    animated = state in _ANIMATED_STATES
    phase = (phase % 1.0) if animated else 0.0

    # Restrained tri-color bloom: atmosphere behind the ring, not visual fog.
    for dx, color_name in ((-0.22, palette.cyan), (0.0, palette.green), (0.22, palette.magenta)):
        glow_center = QPointF(center.x() + diameter * dx, center.y())
        glow = QRadialGradient(glow_center, diameter * 0.52)
        core = QColor(color_name)
        core.setAlpha(18)
        clear = QColor(color_name)
        clear.setAlpha(0)
        glow.setColorAt(0.0, core)
        glow.setColorAt(1.0, clear)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(
            QRectF(
                glow_center.x() - diameter * 0.52,
                glow_center.y() - diameter * 0.52,
                diameter * 1.04,
                diameter * 1.04,
            )
        )

    structural = QColor(palette.secondary)
    structural.setAlpha(42)
    painter.setBrush(Qt.NoBrush)
    for scale in (1.00, 0.83, 0.66):
        d = diameter * scale
        painter.setPen(QPen(structural, max(1.0, short * 0.0021)))
        painter.drawEllipse(QRectF(center.x() - d / 2, center.y() - d / 2, d, d))

    # Two dominant segment layers, plus a quiet technical inner guide.
    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.988,
        short,
        palette,
        segments=8,
        coverage=0.67,
        width_scale=0.018,
        phase_degrees=phase * 105.0,
        alpha=250,
    )
    _draw_segmented_ring(
        painter,
        center,
        diameter * 0.835,
        short,
        palette,
        segments=12,
        coverage=0.31,
        width_scale=0.0068,
        phase_degrees=18.0 - phase * 72.0,
        alpha=168,
    )

    # Sparse radial anchors preserve HUD character without competing with logo.
    for degrees in (-90.0, 0.0, 90.0, 180.0):
        angle = math.radians(degrees)
        inner = diameter * 0.355
        outer = diameter * 0.455
        color = _neon_color_for_angle(palette, degrees)
        color.setAlpha(64)
        painter.setPen(QPen(color, max(1.0, short * 0.0021), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(
            QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner),
            QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer),
        )

    highlighted = int(phase * 24.0) % 24 if animated else -1
    for index in range(24):
        angle = math.radians(index * 15.0 - 90.0)
        inner = diameter * 0.506
        outer = diameter * 0.525
        p1 = QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner)
        p2 = QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer)
        color = QColor(palette.green if index == highlighted else palette.secondary)
        color.setAlpha(220 if index == highlighted else 42)
        painter.setPen(
            QPen(
                color,
                max(1.0, short * (0.0045 if index == highlighted else 0.0016)),
                Qt.SolidLine,
                Qt.RoundCap,
            )
        )
        painter.drawLine(p1, p2)


def _draw_portrait_brand_hud(
    painter: QPainter,
    center: QPointF,
    diameter: float,
    short: float,
    palette: _Theme,
    state: SystemState,
    phase: float,
) -> None:
    """Draw the v9 concentric OwnDash identity HUD from the approved preview."""
    animated = state in _ANIMATED_STATES
    phase = (phase % 1.0) if animated else 0.0

    glow = QRadialGradient(center, diameter * 0.62)
    cyan = QColor(palette.cyan)
    cyan.setAlpha(25)
    magenta = QColor(palette.magenta)
    magenta.setAlpha(12)
    clear = QColor(0, 0, 0, 0)
    glow.setColorAt(0.0, cyan)
    glow.setColorAt(0.60, magenta)
    glow.setColorAt(1.0, clear)
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QRectF(center.x() - diameter * 0.62, center.y() - diameter * 0.62, diameter * 1.24, diameter * 1.24))

    painter.setBrush(Qt.NoBrush)
    structural = QColor(palette.secondary)
    structural.setAlpha(30)
    for scale in (1.00, 0.86, 0.70):
        d = diameter * scale
        painter.setPen(QPen(structural, max(1.0, short * 0.0017)))
        painter.drawEllipse(QRectF(center.x() - d / 2.0, center.y() - d / 2.0, d, d))

    _draw_segmented_ring(
        painter, center, diameter * 0.965, short, palette,
        segments=8, coverage=0.63, width_scale=0.020,
        phase_degrees=phase * 56.0, alpha=248,
    )
    _draw_segmented_ring(
        painter, center, diameter * 0.805, short, palette,
        segments=24, coverage=0.22, width_scale=0.0048,
        phase_degrees=10.0 - phase * 38.0, alpha=165,
    )

    for degrees in (-90.0, 0.0, 90.0, 180.0):
        angle = math.radians(degrees)
        inner = diameter * 0.43
        outer = diameter * 0.515
        color = _neon_color_for_angle(palette, degrees)
        color.setAlpha(190)
        painter.setPen(QPen(color, max(1.2, short * 0.0042), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(
            QPointF(center.x() + math.cos(angle) * inner, center.y() + math.sin(angle) * inner),
            QPointF(center.x() + math.cos(angle) * outer, center.y() + math.sin(angle) * outer),
        )


def _draw_rail_ring_bridges(
    painter: QPainter,
    layout: _PortraitLayout,
    short: float,
    palette: _Theme,
) -> None:
    """Weld every side rail into the outer HUD ring with permanent arcs.

    The animated outer segments are allowed to rotate through gaps. These
    short fixed arcs sit exactly at the four rail docks so no animation phase
    can visually disconnect the frame from the hero circle.
    """
    radius = layout.hud_diameter * 0.494
    for degrees in (35.0, 145.0, 215.0, 325.0):
        color = _neon_color_for_angle(palette, degrees)
        path = QPainterPath(_point_on_circle(layout.hud_center, radius, degrees - 8.0))
        for offset in (-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0):
            path.lineTo(_point_on_circle(layout.hud_center, radius, degrees + offset))
        halo = QColor(color)
        halo.setAlpha(34)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(halo, max(7.0, short * 0.050), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        color.setAlpha(242)
        painter.setPen(QPen(color, max(2.2, short * 0.018), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)


def _draw_side_rails(
    painter: QPainter,
    width: int,
    height: int,
    short: float,
    palette: _Theme,
    *,
    layout: _PortraitLayout | None = None,
) -> None:
    left = QColor(palette.cyan)
    right = QColor(palette.magenta)
    left.setAlpha(145)
    right.setAlpha(145)
    line_width = max(1.0, short * 0.0038)

    if layout is None:
        for x, side, color in ((short * 0.04, 1, left), (width - short * 0.04, -1, right)):
            inward = side * short * 0.075
            painter.setPen(QPen(color, line_width, Qt.SolidLine, Qt.SquareCap))
            painter.drawLine(QPointF(x, height * 0.03), QPointF(x, height * 0.13))
            painter.drawLine(QPointF(x, height * 0.13), QPointF(x + inward, height * 0.22))
            painter.drawLine(QPointF(x + inward, height * 0.22), QPointF(x + inward, height * 0.80))
        return

    upper_left, lower_left, upper_right, lower_right = _portrait_rail_docks(layout)
    approach_ul, approach_ll, approach_ur, approach_lr = _portrait_rail_approaches(layout)

    def draw_one(
        color: QColor,
        *,
        side: int,
        upper: QPointF,
        lower: QPointF,
        upper_approach: QPointF,
        lower_approach: QPointF,
    ) -> None:
        outer_x = width * (0.055 if side > 0 else 0.945)
        track_x = width * (0.115 if side > 0 else 0.885)
        top_y = height * 0.025
        shoulder_y = height * 0.115
        lower_shoulder_y = height * 0.720
        bottom_y = height * 0.905

        upper_path = QPainterPath(QPointF(outer_x, top_y))
        upper_path.lineTo(QPointF(outer_x, shoulder_y))
        upper_path.lineTo(QPointF(track_x, shoulder_y + height * 0.050))
        upper_path.lineTo(QPointF(track_x, upper_approach.y() - short * 0.025))
        upper_path.lineTo(upper_approach)
        upper_path.lineTo(upper)

        lower_path = QPainterPath(lower)
        lower_path.lineTo(lower_approach)
        lower_path.lineTo(QPointF(track_x, lower_approach.y() + short * 0.025))
        lower_path.lineTo(QPointF(track_x, lower_shoulder_y))
        lower_path.lineTo(QPointF(outer_x, lower_shoulder_y + height * 0.050))
        lower_path.lineTo(QPointF(outer_x, bottom_y))

        glow = QColor(color)
        glow.setAlpha(34)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(glow, line_width * 3.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(upper_path)
        painter.drawPath(lower_path)
        painter.setPen(QPen(color, line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(upper_path)
        painter.drawPath(lower_path)

        # A single quiet inner trace adds depth but stops before the HUD itself.
        inner = QColor(color)
        inner.setAlpha(48)
        offset = side * short * 0.026
        painter.setPen(QPen(inner, max(1.0, line_width * 0.58), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(
            QPointF(outer_x + offset, top_y + short * 0.05),
            QPointF(outer_x + offset, shoulder_y),
        )
        painter.drawLine(
            QPointF(track_x + offset, shoulder_y + height * 0.060),
            QPointF(track_x + offset, upper_approach.y() - short * 0.050),
        )
        painter.drawLine(
            QPointF(track_x + offset, lower_approach.y() + short * 0.050),
            QPointF(track_x + offset, lower_shoulder_y - short * 0.02),
        )


    draw_one(
        left,
        side=1,
        upper=upper_left,
        lower=lower_left,
        upper_approach=approach_ul,
        lower_approach=approach_ll,
    )
    draw_one(
        right,
        side=-1,
        upper=upper_right,
        lower=lower_right,
        upper_approach=approach_ur,
        lower_approach=approach_lr,
    )

    # Sparse indicator dots only in the upper frame, away from the hero circle.
    for index in range(3):
        y = height * 0.110 + index * short * 0.050
        radius = max(1.2, short * 0.0038)
        for x, color_name in ((width * 0.083, palette.cyan), (width * 0.917, palette.magenta)):
            color = QColor(color_name)
            color.setAlpha(72 + index * 18)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), radius, radius)


def _draw_background_depth(painter: QPainter, width: int, height: int, short: float, palette: _Theme) -> None:
    center_glow = QRadialGradient(QPointF(width * 0.50, height * 0.225), width * 0.62)
    core = QColor(palette.cyan)
    core.setAlpha(14)
    mid = QColor(palette.magenta)
    mid.setAlpha(5)
    clear = QColor(0, 0, 0, 0)
    center_glow.setColorAt(0.0, core)
    center_glow.setColorAt(0.60, mid)
    center_glow.setColorAt(1.0, clear)
    painter.setPen(Qt.NoPen)
    painter.setBrush(center_glow)
    painter.drawEllipse(QRectF(-width * 0.16, height * 0.045, width * 1.32, width * 1.32))

    scan = QColor(palette.secondary)
    scan.setAlpha(5)
    painter.setPen(QPen(scan, 1.0))
    step = max(100.0, short * 0.28)
    y = height * 0.10
    while y < height * 0.72:
        painter.drawLine(QPointF(width * 0.17, y), QPointF(width * 0.83, y))
        y += step


def _draw_floor_reflection(
    painter: QPainter,
    width: int,
    height: int,
    short: float,
    palette: _Theme,
    *,
    horizon: float | None = None,
) -> None:
    """Draw a restrained v8 lower light reflection without perspective grid."""
    horizon = float(height * 0.855 if horizon is None else horizon)
    line_gradient = QLinearGradient(width * 0.08, horizon, width * 0.92, horizon)
    line_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
    cyan = QColor(palette.cyan)
    green = QColor(palette.green)
    magenta = QColor(palette.magenta)
    cyan.setAlpha(190)
    green.setAlpha(135)
    magenta.setAlpha(190)
    line_gradient.setColorAt(0.24, cyan)
    line_gradient.setColorAt(0.50, green)
    line_gradient.setColorAt(0.76, magenta)
    line_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

    painter.save()
    painter.setOpacity(0.11)
    painter.setPen(QPen(QBrush(line_gradient), max(7.0, short * 0.020), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.10, horizon), QPointF(width * 0.90, horizon))
    painter.setOpacity(0.90)
    painter.setPen(QPen(QBrush(line_gradient), max(2.0, short * 0.0040), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(width * 0.10, horizon), QPointF(width * 0.90, horizon))

    for x_ratio, color_name, alpha in (
        (0.30, palette.cyan, 48),
        (0.50, palette.green, 32),
        (0.70, palette.magenta, 48),
    ):
        glow = QRadialGradient(QPointF(width * x_ratio, horizon + short * 0.08), short * 0.42)
        color = QColor(color_name)
        color.setAlpha(alpha)
        clear = QColor(color_name)
        clear.setAlpha(0)
        glow.setColorAt(0.0, color)
        glow.setColorAt(1.0, clear)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(
            width * x_ratio - short * 0.42,
            horizon - short * 0.03,
            short * 0.84,
            short * 0.62,
        ))

    for x_ratio, color_name in ((0.31, palette.cyan), (0.50, palette.green), (0.69, palette.magenta)):
        color = QColor(color_name)
        color.setAlpha(110)
        fade = QLinearGradient(0, horizon, 0, horizon + short * 0.38)
        fade.setColorAt(0.0, color)
        tail = QColor(color_name)
        tail.setAlpha(0)
        fade.setColorAt(1.0, tail)
        painter.setPen(QPen(QBrush(fade), max(2.0, short * 0.007), Qt.SolidLine, Qt.RoundCap))
        x = width * x_ratio
        painter.drawLine(QPointF(x, horizon), QPointF(x, min(height, horizon + short * 0.38)))
    painter.restore()


def _fallback_state_detail(state: SystemState, title: str) -> str:
    english_titles = {
        "idle", "system locked", "standby", "system transition",
        "shutting down", "restarting",
    }
    english = title.strip().lower() in english_titles
    if english:
        return {
            SystemState.IDLE: "Waiting for activity",
            SystemState.LOCKED: "System is locked",
            SystemState.SUSPENDING: "Entering standby",
            SystemState.TRANSITIONING: "OwnDash is ending the current session",
            SystemState.SHUTTING_DOWN: "System is shutting down safely",
            SystemState.RESTARTING: "System is restarting",
        }[state]
    return {
        SystemState.IDLE: "Warten auf Aktivität",
        SystemState.LOCKED: "System ist gesperrt",
        SystemState.SUSPENDING: "Standby wird vorbereitet",
        SystemState.TRANSITIONING: "OwnDash beendet die aktuelle Sitzung",
        SystemState.SHUTTING_DOWN: "System wird sicher beendet",
        SystemState.RESTARTING: "System wird neu gestartet",
    }[state]


def _draw_state_icon(
    painter: QPainter,
    rect: QRectF,
    state: SystemState,
    palette: _Theme,
    short: float,
) -> None:
    center = rect.center()
    accent = QColor(_STATE_ACCENTS[state])
    halo = QRadialGradient(center, rect.width() * 0.78)
    glow = QColor(accent)
    glow.setAlpha(46)
    clear = QColor(accent)
    clear.setAlpha(0)
    halo.setColorAt(0.0, glow)
    halo.setColorAt(1.0, clear)
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(halo)
    painter.drawEllipse(rect.adjusted(-short * 0.018, -short * 0.018, short * 0.018, short * 0.018))

    pen = QPen(QColor(palette.primary), max(2.0, short * 0.007), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

    if state is SystemState.LOCKED:
        body = QRectF(x + w * 0.22, y + h * 0.46, w * 0.56, h * 0.43)
        painter.drawRoundedRect(body, w * 0.08, w * 0.08)
        shackle = QRectF(x + w * 0.31, y + h * 0.12, w * 0.38, h * 0.52)
        painter.drawArc(shackle, 0, 180 * 16)
        painter.drawLine(QPointF(shackle.left(), shackle.center().y()), QPointF(shackle.left(), body.top()))
        painter.drawLine(QPointF(shackle.right(), shackle.center().y()), QPointF(shackle.right(), body.top()))
    elif state is SystemState.SHUTTING_DOWN:
        circle = QRectF(x + w * 0.18, y + h * 0.18, w * 0.64, h * 0.64)
        painter.drawArc(circle, 40 * 16, 280 * 16)
        painter.drawLine(QPointF(center.x(), y + h * 0.08), QPointF(center.x(), y + h * 0.46))
    elif state is SystemState.RESTARTING:
        circle = QRectF(x + w * 0.17, y + h * 0.17, w * 0.66, h * 0.66)
        painter.drawArc(circle, 30 * 16, 285 * 16)
        arrow = QPainterPath(QPointF(x + w * 0.77, y + h * 0.17))
        arrow.lineTo(QPointF(x + w * 0.82, y + h * 0.38))
        arrow.lineTo(QPointF(x + w * 0.62, y + h * 0.31))
        arrow.closeSubpath()
        painter.setBrush(QColor(palette.primary))
        painter.drawPath(arrow)
    elif state in (SystemState.SUSPENDING, SystemState.IDLE):
        painter.drawArc(QRectF(x + w * 0.20, y + h * 0.15, w * 0.58, h * 0.70), 70 * 16, 220 * 16)
        painter.drawArc(QRectF(x + w * 0.34, y + h * 0.13, w * 0.46, h * 0.68), 105 * 16, 170 * 16)
    else:
        for offset in (-0.22, 0.0, 0.22):
            cx = center.x() + w * offset
            painter.drawEllipse(QPointF(cx, center.y()), w * 0.055, w * 0.055)
    painter.restore()


def _draw_state_rail(painter: QPainter, rect: QRectF, palette: _Theme, state: SystemState, phase: float) -> None:
    gradient = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    gradient.setColorAt(0.0, QColor(palette.cyan))
    gradient.setColorAt(0.48, QColor(palette.green))
    gradient.setColorAt(1.0, QColor(palette.magenta))
    painter.save()
    painter.setOpacity(0.12)
    painter.setPen(QPen(QBrush(gradient), max(5.0, rect.height() * 1.45), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(rect.left(), rect.center().y()), QPointF(rect.right(), rect.center().y()))
    painter.setOpacity(1.0)
    painter.setPen(QPen(QBrush(gradient), max(1.3, rect.height() * 0.18), Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(rect.left(), rect.center().y()), QPointF(rect.right(), rect.center().y()))

    scanner_ratio = 0.50
    if state in _ANIMATED_STATES:
        scanner_ratio = 0.14 + 0.72 * (0.5 + 0.5 * math.sin(phase * math.tau - math.pi / 2))
    elif state is SystemState.RESTARTING:
        scanner_ratio = 0.68
    elif state is SystemState.SHUTTING_DOWN:
        scanner_ratio = 0.82
    elif state is SystemState.SUSPENDING:
        scanner_ratio = 0.58
    scanner_x = rect.left() + rect.width() * scanner_ratio
    glow = QColor(_STATE_ACCENTS[state])
    glow.setAlpha(48)
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QPointF(scanner_x, rect.center().y()), rect.height() * 0.74, rect.height() * 0.74)
    painter.setBrush(QColor(palette.primary))
    painter.drawEllipse(QPointF(scanner_x, rect.center().y()), rect.height() * 0.17, rect.height() * 0.17)
    painter.restore()


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
    """Render one full-bleed OwnDash system-state frame."""
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

    background = QLinearGradient(0, 0, width * 0.72, height)
    background.setColorAt(0.0, QColor(palette.top))
    background.setColorAt(0.46, QColor(palette.middle))
    background.setColorAt(1.0, QColor(palette.bottom))
    painter.fillRect(image.rect(), background)

    short = float(min(width, height))
    portrait = height >= width * 1.35
    title, detail = _state_text(state, strings)
    _draw_background_depth(painter, width, height, short, palette)

    if portrait:
        layout = _portrait_layout(width, height)
        _draw_side_rails(painter, width, height, short, palette, layout=layout)
        _draw_portrait_brand_hud(painter, layout.hud_center, layout.hud_diameter, short, palette, state, phase)
        _draw_rail_ring_bridges(painter, layout, short, palette)
        _draw_brand_icon(painter, icon, layout.brand_icon_rect, short, palette)
        _draw_gradient_wordmark(painter, image, layout.wordmark_rect, palette, layout.wordmark_font_px)

        # A single luminous separator mirrors the approved reference without
        # adding another box around the state information.
        separator_y = height * 0.405
        separator = QLinearGradient(width * 0.18, separator_y, width * 0.82, separator_y)
        transparent = QColor(0, 0, 0, 0)
        cyan_sep = QColor(palette.cyan)
        cyan_sep.setAlpha(175)
        magenta_sep = QColor(palette.magenta)
        magenta_sep.setAlpha(145)
        separator.setColorAt(0.0, transparent)
        separator.setColorAt(0.38, cyan_sep)
        separator.setColorAt(0.62, magenta_sep)
        separator.setColorAt(1.0, transparent)
        painter.setPen(QPen(QBrush(separator), max(1.2, short * 0.0030), Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(width * 0.18, separator_y), QPointF(width * 0.82, separator_y))

        _draw_state_icon(painter, layout.status_icon_rect, state, palette, short)
        _draw_centered_single_line(
            painter,
            image,
            layout.status_rect,
            title.upper(),
            layout.status_font_px,
            palette.primary,
            bold=True,
            glow=accent.name(),
            family="DejaVu Sans Condensed",
        )
        status_detail = detail or _fallback_state_detail(state, title)
        _draw_centered_single_line(
            painter,
            image,
            layout.detail_rect,
            status_detail,
            layout.detail_font_px,
            palette.secondary,
            glow=accent.name(),
            family="DejaVu Sans Condensed",
        )

        _draw_state_rail(painter, layout.bar_rect, palette, state, phase)

        context_y = layout.context_top
        if clock_text:
            _draw_centered_single_line(
                painter,
                image,
                QRectF(width * 0.12, context_y, width * 0.76, height * 0.055),
                clock_text,
                width * 0.105,
                palette.primary,
                bold=True,
                glow=palette.cyan,
                family="DejaVu Sans Condensed",
            )
            context_y += height * 0.057
        if date_text and state is SystemState.LOCKED:
            _draw_centered_single_line(
                painter,
                image,
                QRectF(width * 0.15, context_y, width * 0.70, height * 0.030),
                date_text,
                width * 0.035,
                palette.secondary,
                family="DejaVu Sans Condensed",
            )
            context_y += height * 0.034
        if sensor_text and state in _ANIMATED_STATES:
            _draw_centered_single_line(
                painter,
                image,
                QRectF(width * 0.10, context_y, width * 0.80, height * 0.028),
                sensor_text,
                width * 0.025,
                palette.muted,
                family="DejaVu Sans Condensed",
            )

        _draw_floor_reflection(painter, width, height, short, palette, horizon=layout.floor_horizon)
        _draw_centered_single_line(
            painter,
            image,
            QRectF(width * 0.18, height * 0.944, width * 0.64, height * 0.022),
            f"{APP_NAME} · {__version__}",
            width * 0.020,
            palette.muted,
            family="DejaVu Sans Condensed",
        )
    else:
        _draw_side_rails(painter, width, height, short, palette)
        center = QPointF(width * 0.36, height * 0.48)
        diameter = min(height * 0.86, width * 0.44)
        _draw_hud_rings(painter, center, diameter, short, palette, state, phase)
        _draw_gradient_wordmark(
            painter,
            image,
            QRectF(width * 0.51, height * 0.19, width * 0.44, height * 0.19),
            palette,
            short * 0.16,
        )
        _draw_centered(
            painter,
            image,
            QRectF(width * 0.49, height * 0.40, width * 0.46, height * 0.17),
            title.upper(),
            short * 0.105,
            palette.primary,
            bold=True,
            glow=accent.name(),
            family="DejaVu Sans Condensed",
        )
        if detail:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.53, height * 0.56, width * 0.39, height * 0.09),
                detail,
                short * 0.047,
                palette.secondary,
            )
        bar = QRectF(width * 0.58, height * 0.70, width * 0.29, max(9.0, short * 0.026))
        _draw_state_rail(painter, bar, palette, state, phase)
        context = " · ".join(
            part
            for part in (
                clock_text or "",
                date_text if state is SystemState.LOCKED else "",
                sensor_text if state in _ANIMATED_STATES else "",
            )
            if part
        )
        if context:
            _draw_centered(
                painter,
                image,
                QRectF(width * 0.50, height * 0.79, width * 0.45, height * 0.09),
                context,
                short * 0.040,
                palette.secondary,
            )

    painter.end()
    return image