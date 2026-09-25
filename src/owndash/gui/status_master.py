"""Approved raster-backed portrait status screens for the 480x1920 panel."""
from __future__ import annotations

import base64
from functools import lru_cache
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen

from owndash.core.system_state import SystemState
from ._status_master_data_00 import DATA as DATA_00
from ._status_master_data_01 import DATA as DATA_01
from ._status_master_data_02 import DATA as DATA_02
from ._status_master_data_03 import DATA as DATA_03
from ._status_master_data_04 import DATA as DATA_04
from ._status_master_data_05 import DATA as DATA_05


@lru_cache(maxsize=1)
def _master_image() -> QImage:
    payload = base64.b64decode(DATA_00 + DATA_01 + DATA_02 + DATA_03 + DATA_04 + DATA_05)
    image = QImage.fromData(payload, "JPG")
    if image.isNull() or image.width() != 480 or image.height() != 1920:
        raise RuntimeError("invalid approved OwnDash status master artwork")
    return image.convertToFormat(QImage.Format_RGB32)


def _fit_single_line(image: QImage, text: str, rect: QRectF, px: int) -> QFont:
    font = QFont("DejaVu Sans")
    font.setWeight(QFont.Weight.Medium)
    font.setPixelSize(px)
    while font.pixelSize() > 10:
        metrics = QFontMetricsF(font, image)
        if metrics.horizontalAdvance(text) <= rect.width() and metrics.height() <= rect.height():
            break
        font.setPixelSize(font.pixelSize() - 1)
    return font


def _draw_text(painter: QPainter, image: QImage, rect: QRectF, text: str, px: int, *, glow: bool = False) -> None:
    if not text:
        return
    font = _fit_single_line(image, text, rect, px)
    painter.setFont(font)
    flags = Qt.AlignCenter | Qt.AlignVCenter
    if glow:
        halo = QColor("#00e7ff")
        for dx, dy, alpha in ((-2, 0, 18), (2, 0, 18), (0, -2, 15), (0, 2, 15), (-1, 0, 35), (1, 0, 35)):
            halo.setAlpha(alpha)
            painter.setPen(halo)
            painter.drawText(rect.translated(dx, dy), flags, text)
    painter.setPen(QColor("#f7fcff") if glow else QColor("#d9edf7"))
    painter.drawText(rect, flags, text)


def _state_copy(state: SystemState, strings: dict[str, str]) -> tuple[str, str]:
    if state is SystemState.LOCKED:
        return "GESPERRT", "System ist gesperrt"
    if state is SystemState.IDLE:
        return "BEREIT", "Warten auf Aktivität"
    if state is SystemState.SUSPENDING:
        return "STANDBY", "Standby wird vorbereitet"
    if state is SystemState.TRANSITIONING:
        return "SYSTEMWECHSEL", "Aktuelle Sitzung wird beendet"
    if state is SystemState.SHUTTING_DOWN:
        return "HERUNTERFAHREN", "System wird sicher beendet"
    if state is SystemState.RESTARTING:
        return "NEUSTART", "System wird neu gestartet"
    return str(state.value).upper(), ""


def render_status_master(
    state: SystemState,
    strings: dict[str, str],
    clock_text: str | None,
    date_text: str | None,
    animation_phase: float,
) -> QImage:
    """Render the approved 480x1920 master while keeping system state live."""
    image = _master_image().copy()
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    if state is not SystemState.LOCKED:
        # Preserve the approved ring, rails and floor exactly; replace only the
        # state block from the locked master with the current system state.
        painter.fillRect(QRectF(38, 700, 404, 360), QColor(1, 7, 12, 248))
        headline, detail = _state_copy(state, strings)
        _draw_text(painter, image, QRectF(38, 800, 404, 78), headline, 46, glow=True)
        _draw_text(painter, image, QRectF(60, 884, 360, 48), detail, 20)
        bar_y = 968.0
        painter.setPen(QPen(QColor("#00e7ff"), 4.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(92, bar_y), QPointF(240, bar_y))
        painter.setPen(QPen(QColor("#ff2aae"), 4.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(240, bar_y), QPointF(388, bar_y))

    _draw_text(painter, image, QRectF(105, 1110, 270, 92), clock_text or "", 52, glow=True)
    if state is SystemState.LOCKED:
        _draw_text(painter, image, QRectF(110, 1190, 260, 44), date_text or "", 20)

    if state in (SystemState.LOCKED, SystemState.IDLE):
        phase = float(animation_phase) % 1.0
        scanner_x = 138.0 + 204.0 * (0.5 + 0.5 * math.sin(phase * math.tau - math.pi / 2.0))
        scanner = QColor("#f7fcff")
        scanner.setAlpha(120)
        painter.setPen(QPen(scanner, 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawPoint(QPointF(scanner_x, 947.0))

    painter.end()
    return image


def render_locked_master(clock_text: str | None, date_text: str | None, animation_phase: float) -> QImage:
    return render_status_master(SystemState.LOCKED, {}, clock_text, date_text, animation_phase)
