from __future__ import annotations

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage

from owndash.gui.system_state_frame import _fit_detail_text
from owndash.gui.system_state_layout import LayoutClass, classify_layout, layout_for_size


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        (480, 1920, LayoutClass.ULTRA_PORTRAIT),
        (720, 1280, LayoutClass.PORTRAIT),
        (800, 1280, LayoutClass.PORTRAIT),
        (1024, 1024, LayoutClass.NEAR_SQUARE),
        (1024, 600, LayoutClass.LANDSCAPE),
        (1280, 800, LayoutClass.LANDSCAPE),
        (1920, 1080, LayoutClass.LANDSCAPE),
        (2560, 1440, LayoutClass.LANDSCAPE),
    ],
)
def test_representative_sizes_use_expected_layout_class(width, height, expected):
    assert classify_layout(width, height) is expected


def test_layout_class_thresholds_are_deterministic():
    assert classify_layout(37, 100) is LayoutClass.ULTRA_PORTRAIT
    assert classify_layout(38, 100) is LayoutClass.PORTRAIT
    assert classify_layout(77, 100) is LayoutClass.PORTRAIT
    assert classify_layout(78, 100) is LayoutClass.NEAR_SQUARE
    assert classify_layout(125, 100) is LayoutClass.NEAR_SQUARE
    assert classify_layout(126, 100) is LayoutClass.LANDSCAPE


@pytest.mark.parametrize("width,height", [(0, 100), (100, 0), (-1, 100), (100, -1)])
def test_layout_rejects_non_positive_dimensions(width, height):
    with pytest.raises(ValueError, match="positive"):
        classify_layout(width, height)
    with pytest.raises(ValueError, match="positive"):
        layout_for_size(width, height)


@pytest.mark.parametrize(
    "width,height",
    [
        (480, 1920),
        (720, 1280),
        (800, 1280),
        (1024, 1024),
        (1024, 600),
        (1280, 800),
        (1920, 1080),
        (2560, 1440),
        (240, 1920),
        (3440, 480),
    ],
)
def test_all_layout_zones_stay_inside_target_and_safe_area(width, height):
    layout = layout_for_size(width, height)
    target = layout.target
    safe = layout.safe

    assert target.left() == 0
    assert target.top() == 0
    assert target.width() == width
    assert target.height() == height
    assert target.contains(safe)

    for rect in (
        layout.art,
        layout.title,
        layout.detail,
        layout.clock,
        layout.date,
        layout.accent,
        layout.footer,
    ):
        assert safe.contains(rect), (layout.layout_class, rect, safe)
        assert rect.width() > 0
        assert rect.height() > 0


def test_landscape_layout_places_art_and_information_side_by_side():
    layout = layout_for_size(1920, 1080)
    assert layout.layout_class is LayoutClass.LANDSCAPE
    assert layout.art.right() < layout.title.left()
    assert layout.art.right() < layout.clock.left()


def test_portrait_layout_keeps_vertical_visual_hierarchy():
    layout = layout_for_size(800, 1280)
    assert layout.layout_class is LayoutClass.PORTRAIT
    assert layout.art.bottom() <= layout.title.top()
    assert layout.title.bottom() <= layout.detail.bottom()
    assert layout.detail.bottom() <= layout.clock.top()
    assert layout.clock.bottom() <= layout.footer.top()


def test_ultra_portrait_preserves_reference_ordering():
    layout = layout_for_size(480, 1920)
    assert layout.layout_class is LayoutClass.ULTRA_PORTRAIT
    assert layout.art.top() < layout.title.top() < layout.clock.top() < layout.footer.top()


def test_detail_text_wraps_to_at_most_two_lines_without_dropping_words():
    image = QImage(500, 200, QImage.Format_RGB32)
    rect = QRectF(0, 0, 250, 70)
    text = "OwnDash is ending the current Linux desktop session safely"

    _font, wrapped = _fit_detail_text(image, text, rect, 24)

    assert "\n" in wrapped
    assert wrapped.count("\n") <= 1
    assert wrapped.replace("\n", " ") == text
