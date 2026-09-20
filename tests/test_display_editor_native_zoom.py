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


def test_detected_usb_display_switches_editor_to_native_100_percent(window):
    window.canvas.auto_fit = True
    window.canvas.resetTransform()
    window.canvas.scale(0.25, 0.25)

    window._display_connected(DisplayInfo("VSDisplay", 1920, 480))

    assert (window.canvas.canvas_size.width, window.canvas.canvas_size.height) == (480, 1920)
    assert window.canvas.auto_fit is False
    assert math.isclose(window.canvas.transform().m11(), 1.0, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(window.canvas.transform().m22(), 1.0, rel_tol=0.0, abs_tol=1e-9)


def test_portrait_status_branding_is_present_but_status_remains_primary():
    layout = _portrait_layout(480, 1920)

    assert layout.wordmark_font_px >= 480 * 0.11
    assert layout.brand_icon_rect.width() >= 480 * 0.12
    assert layout.status_font_px > layout.wordmark_font_px
    assert layout.status_font_px <= layout.wordmark_font_px * 1.35
    assert layout.wordmark_rect.width() >= 480 * 0.76
    assert layout.brand_icon_rect.bottom() < layout.wordmark_rect.top()
    assert layout.wordmark_rect.bottom() < layout.status_rect.top()
