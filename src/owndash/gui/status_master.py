"""Approved raster-backed portrait status screen.

The locked 480x1920 VSDisplay path deliberately uses the approved master
artwork instead of reconstructing it procedurally. Only live clock/date text
and a tiny lock-animation scanner point are painted at runtime.
"""
from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen


_MASTER_NAME = "status-master-locked-480x1920.jpg"


@lru_cache(maxsize=1)
def _master_image() -> QImage:
    resource = files("owndash").joinpath("assets", _MASTER_NAME)
    image = QImage.fromData(resource.read_bytes(), "JPG")
    if image.isNull() or image.width() != 480 or image.height() != 1920:
        raise RuntimeError("invalid approved OwnDash status master artwork")
    return image


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


def _draw_live_text(painter: QPainter, image: QImage, rect: QRectF, text: str, px: int, *, glow: bool) -> None:
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


def render_locked_master(clock_text: str | None, date_text: str | None, animation_phase: float) -> QImage:
    """Return the exact approved 480x1920 locked design with live context."""
    image = _master_image().copy()
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    # These boxes match the clock/date positions of the approved reference.
    _draw_live_text(painter, image, QRectF(105, 1110, 270, 92), clock_text or "", 52, glow=True)
    _draw_live_text(painter, image, QRectF(110, 1190, 260, 44), date_text or "", 20, glow=False)

    # Preserve a very subtle animated cue so LOCKED remains a live state while
    # the approved raster composition itself stays untouched.
    phase = float(animation_phase) % 1.0
    scanner_x = 138.0 + 204.0 * (0.5 + 0.5 * math.sin(phase * math.tau - math.pi / 2.0))
    scanner = QColor("#f7fcff")
    scanner.setAlpha(95)
    painter.setPen(QPen(scanner, 2.0, Qt.SolidLine, Qt.RoundCap))
    painter.drawPoint(QPointF(scanner_x, 947.0))

    painter.end()
    return image
