"""Responsive geometry for OwnDash system-state screens."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QRectF


class LayoutClass(str, Enum):
    ULTRA_PORTRAIT = "ultra_portrait"
    PORTRAIT = "portrait"
    NEAR_SQUARE = "near_square"
    LANDSCAPE = "landscape"


@dataclass(frozen=True, slots=True)
class SystemStateLayout:
    layout_class: LayoutClass
    target: QRectF
    safe: QRectF
    art: QRectF
    title: QRectF
    detail: QRectF
    clock: QRectF
    date: QRectF
    accent: QRectF
    footer: QRectF


def _validate_size(width: int, height: int) -> tuple[int, int]:
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0:
        raise ValueError("system-state frame dimensions must be positive")
    return width, height


def classify_layout(width: int, height: int) -> LayoutClass:
    """Classify a target by aspect ratio, never by a known-resolution list."""
    width, height = _validate_size(width, height)
    ratio = width / height
    if ratio < 0.38:
        return LayoutClass.ULTRA_PORTRAIT
    if ratio < 0.78:
        return LayoutClass.PORTRAIT
    if ratio <= 1.25:
        return LayoutClass.NEAR_SQUARE
    return LayoutClass.LANDSCAPE


def _relative(width: int, height: int, x: float, y: float, w: float, h: float) -> QRectF:
    return QRectF(width * x, height * y, width * w, height * h)


def layout_for_size(width: int, height: int) -> SystemStateLayout:
    """Return target-space composition zones for a system-state frame."""
    width, height = _validate_size(width, height)
    layout_class = classify_layout(width, height)
    target = QRectF(0.0, 0.0, float(width), float(height))

    if layout_class is LayoutClass.ULTRA_PORTRAIT:
        safe = _relative(width, height, 0.04, 0.02, 0.92, 0.94)
        return SystemStateLayout(
            layout_class,
            target,
            safe,
            _relative(width, height, 55 / 480, 267 / 1920, 370 / 480, 370 / 1920),
            _relative(width, height, 55 / 480, 760 / 1920, 370 / 480, 82 / 1920),
            _relative(width, height, 55 / 480, 842 / 1920, 370 / 480, 48 / 1920),
            _relative(width, height, 100 / 480, 1082 / 1920, 280 / 480, 80 / 1920),
            _relative(width, height, 100 / 480, 1160 / 1920, 280 / 480, 44 / 1920),
            _relative(width, height, 65 / 480, 918 / 1920, 350 / 480, 8 / 1920),
            _relative(width, height, 110 / 480, 1435 / 1920, 260 / 480, 36 / 1920),
        )

    if layout_class is LayoutClass.PORTRAIT:
        safe = _relative(width, height, 0.05, 0.03, 0.90, 0.94)
        return SystemStateLayout(
            layout_class,
            target,
            safe,
            _relative(width, height, 0.17, 0.06, 0.66, 0.36),
            _relative(width, height, 0.10, 0.45, 0.80, 0.08),
            _relative(width, height, 0.10, 0.535, 0.80, 0.065),
            _relative(width, height, 0.20, 0.66, 0.60, 0.10),
            _relative(width, height, 0.20, 0.765, 0.60, 0.05),
            _relative(width, height, 0.15, 0.615, 0.70, 0.008),
            _relative(width, height, 0.25, 0.90, 0.50, 0.04),
        )

    if layout_class is LayoutClass.NEAR_SQUARE:
        safe = _relative(width, height, 0.04, 0.04, 0.92, 0.92)
        return SystemStateLayout(
            layout_class,
            target,
            safe,
            _relative(width, height, 0.06, 0.15, 0.42, 0.55),
            _relative(width, height, 0.54, 0.23, 0.40, 0.10),
            _relative(width, height, 0.54, 0.34, 0.40, 0.14),
            _relative(width, height, 0.58, 0.55, 0.32, 0.12),
            _relative(width, height, 0.58, 0.68, 0.32, 0.07),
            _relative(width, height, 0.54, 0.50, 0.40, 0.01),
            _relative(width, height, 0.28, 0.91, 0.44, 0.04),
        )

    safe = _relative(width, height, 0.04, 0.04, 0.92, 0.92)
    return SystemStateLayout(
        layout_class,
        target,
        safe,
        _relative(width, height, 0.06, 0.15, 0.40, 0.65),
        _relative(width, height, 0.53, 0.20, 0.41, 0.12),
        _relative(width, height, 0.53, 0.34, 0.41, 0.12),
        _relative(width, height, 0.58, 0.55, 0.31, 0.13),
        _relative(width, height, 0.58, 0.69, 0.31, 0.07),
        _relative(width, height, 0.54, 0.49, 0.39, 0.01),
        _relative(width, height, 0.53, 0.90, 0.41, 0.04),
    )
