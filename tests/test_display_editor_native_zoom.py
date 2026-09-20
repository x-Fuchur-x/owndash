from __future__ import annotations

import math

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from owndash.core.display import DisplayInfo
from owndash.core.preferences import AppPreferences
from owndash.gui.app_window import SafeShutdownWindow
from owndash.gui.system_state_frame import _portrait_layout


@pytest.fixture
def window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "owndash.gui.main_window.load_preferences",
        lambda: AppPreferences(setup_completed=True, check_updates=False),
    )
    monkeypatch.setattr("owndash.gui.main_window.SystemSensorProvider.snapshot", lambda self: {})
    current = SafeShutdownWindow()
    current._display_rotation = 90
    monkeypatch.setattr(current, "_push_display_frame", lambda: None)
    yield current
    for timer in current.findChildren(QTimer):
        timer.stop()
    current.hide()
    current.deleteLater()
    app.processEvents()


def _expected_fit_width_scale(window) -> float:
    # Keep a small editor gutter so the canvas reads as a deliberate artboard
    # instead of touching the viewport edge. The production code uses the same
    # 24 px gutter on both sides.
    usable_width = max(1, window.canvas.viewport().width() - 48)
    return max(0.01, min(3.0, usable_width / window.canvas.canvas_size.width))


def test_detected_usb_display_uses_fit_width_working_view(window):
    app = QApplication.instance()
    window.resize(1400, 900)
    window.show()
    app.processEvents()

    window.canvas.auto_fit = True
    window.canvas.resetTransform()
    window.canvas.scale(0.25, 0.25)

    window._display_connected(DisplayInfo("VSDisplay", 1920, 480))
    app.processEvents()

    assert (window.canvas.canvas_size.width, window.canvas.canvas_size.height) == (480, 1920)
    assert window.canvas.auto_fit is False
    assert getattr(window.canvas, "auto_fit_width", False) is True
    expected = _expected_fit_width_scale(window)
    assert math.isclose(window.canvas.transform().m11(), expected, rel_tol=0.0, abs_tol=0.02)
    assert math.isclose(window.canvas.transform().m22(), expected, rel_tol=0.0, abs_tol=0.02)


def test_fit_width_starts_at_top_when_activated(window):
    app = QApplication.instance()
    window.resize(1200, 760)
    window.show()
    app.processEvents()

    window.canvas.fit_canvas_width()
    app.processEvents()

    bar = window.canvas.verticalScrollBar()
    assert bar.value() == bar.minimum()


def test_fit_width_resize_preserves_current_vertical_work_position(window):
    app = QApplication.instance()
    window.resize(1120, 760)
    window.show()
    app.processEvents()

    window._display_connected(DisplayInfo("VSDisplay", 1920, 480))
    app.processEvents()

    bar = window.canvas.verticalScrollBar()
    assert bar.maximum() > bar.minimum()
    bar.setValue(int(bar.maximum() * 0.58))
    app.processEvents()
    before_y = window.canvas.mapToScene(window.canvas.viewport().rect().center()).y()

    window.resize(1580, 900)
    app.processEvents()
    window.canvas._fit_if_enabled()
    app.processEvents()
    after_y = window.canvas.mapToScene(window.canvas.viewport().rect().center()).y()

    assert abs(after_y - before_y) <= 6.0


def test_fit_width_tracks_window_size_but_manual_100_percent_does_not(window):
    app = QApplication.instance()
    window.resize(1120, 760)
    window.show()
    app.processEvents()

    window._display_connected(DisplayInfo("VSDisplay", 1920, 480))
    app.processEvents()
    first_scale = window.canvas.transform().m11()

    window.resize(1580, 900)
    app.processEvents()
    window.canvas._fit_if_enabled()
    fitted_scale = window.canvas.transform().m11()

    assert getattr(window.canvas, "auto_fit_width", False) is True
    assert fitted_scale > first_scale
    assert math.isclose(fitted_scale, _expected_fit_width_scale(window), rel_tol=0.0, abs_tol=0.02)

    window._reset_zoom()
    assert window.canvas.auto_fit is False
    assert getattr(window.canvas, "auto_fit_width", False) is False
    assert math.isclose(window.canvas.transform().m11(), 1.0, rel_tol=0.0, abs_tol=1e-9)

    window.resize(1260, 780)
    app.processEvents()
    window.canvas._fit_if_enabled()
    assert math.isclose(window.canvas.transform().m11(), 1.0, rel_tol=0.0, abs_tol=1e-9)


def test_portrait_status_branding_is_present_but_status_remains_primary():
    layout = _portrait_layout(480, 1920)

    assert layout.wordmark_font_px >= 480 * 0.11
    assert layout.brand_icon_rect.width() >= 480 * 0.12
    assert layout.status_font_px > layout.wordmark_font_px
    assert layout.status_font_px <= layout.wordmark_font_px * 1.35
    assert layout.wordmark_rect.width() >= 480 * 0.76
    assert layout.brand_icon_rect.bottom() < layout.wordmark_rect.top()
    assert layout.wordmark_rect.bottom() < layout.status_rect.top()
