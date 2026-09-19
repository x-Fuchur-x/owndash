"""Regressions for mixed-DPI monitor output and non-destructive layout fitting."""
import json
import os
import subprocess
import sys

import pytest
from PySide6.QtCore import QPointF, QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QDialog

from owndash.core.models import DashboardPage, Profile, WidgetConfig
from owndash.core.preferences import AppPreferences
from owndash.gui.canvas import CanvasSize, DashboardCanvas
from owndash.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("owndash.gui.main_window.load_preferences", lambda: AppPreferences(setup_completed=True))
    # Sensor reads are external to the display behavior being tested.
    monkeypatch.setattr("owndash.gui.main_window.SystemSensorProvider.snapshot", lambda self: {})
    w = MainWindow()
    w.show()
    app.processEvents()
    yield w
    for timer in w.findChildren(QTimer):
        timer.stop()
    w.hide()
    w.deleteLater()
    app.processEvents()


def test_mixed_dpi_resolution_and_fullscreen_target(tmp_path):
    config = tmp_path / "screens.json"
    config.write_text(json.dumps({"screens": [
        {"name": "HDMI-A-1", "x": 3440, "y": 0, "width": 3840, "height": 2160, "dpr": 1},
        {"name": "DP-1", "x": 0, "y": 0, "width": 3440, "height": 1440, "dpr": 1},
    ]}))
    script = '''
from PySide6.QtCore import Qt
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from owndash.gui.main_window import MainWindow
from owndash.hardware.screen_display import ScreenPresenter
app = QApplication([])
devices = MainWindow._available_screen_devices(None)
by_name = {d[1]: d for d in devices}
assert by_name["HDMI-A-1"][2:4] == (3840, 2160), devices
assert by_name["DP-1"][2:4] == (3440, 1440), devices
for target in app.screens():
    presenter = ScreenPresenter(target.geometry(), screen=target)
    presenter.open()
    app.processEvents()
    assert presenter.window.windowHandle().screen() is target
    image = QImage(3840, 2160, QImage.Format_RGB32)
    image.fill(Qt.red)
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "JPEG")
    presenter._show_frame(bytes(buffer.data()))
    shown = presenter.label.pixmap()
    assert shown.devicePixelRatio() == target.devicePixelRatio()
    if target.name() == "HDMI-A-1":
        assert (shown.width(), shown.height()) == (3840, 2160)
    presenter._close()
# Exercise the chooser identity -> real backend -> native window path too.
import owndash.gui.main_window as mw
from owndash.core.preferences import AppPreferences
from PySide6.QtWidgets import QMessageBox
mw.load_preferences = lambda: AppPreferences(setup_completed=True)
mw.SystemSensorProvider.snapshot = lambda self: {}
mw.DisplayStreamer.start = lambda self: None  # no worker needed for this GUI contract
QMessageBox.question = lambda *args: QMessageBox.Yes
w = MainWindow()
w.display_backend_key = "screen"
w.display_device_id = by_name["HDMI-A-1"][0]
w._display_rotation = 0
w._start_display_stream()
info = w.display_streamer.backend.connect()
assert (info.width, info.height) == (3840, 2160)
w._screen_presenter.open()
app.processEvents()
assert w._screen_presenter.window.windowHandle().screen().name() == "HDMI-A-1"
w._stop_display_stream()
w.hide()
'''
    env = dict(os.environ, QT_QPA_PLATFORM=f"offscreen:configfile={config}", QT_SCREEN_SCALE_FACTORS="HDMI-A-1=2;DP-1=1", XDG_CONFIG_HOME=str(tmp_path))
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_switch_to_monitor_defaults_to_upright_and_preserves_usb_choice(window, monkeypatch):
    def choose(dialog):
        backend, device, rotation = dialog.findChildren(QComboBox)
        assert rotation.currentData() == 270
        backend.setCurrentIndex(backend.findData("screen"))
        assert rotation.currentData() == 0
        rotation.setCurrentIndex(rotation.findData(90))
        backend.setCurrentIndex(backend.findData("aic_usb"))
        assert rotation.currentData() == 270
        backend.setCurrentIndex(backend.findData("screen"))
        assert rotation.currentData() == 90
        return QDialog.Accepted
    monkeypatch.setattr(QDialog, "exec", choose)
    window._open_display_settings()
    assert window._profile_from_canvas().rotation == 90


def test_resize_preserves_widget_aspect_and_places_against_new_bounds(app):
    canvas = DashboardCanvas(size=CanvasSize(480, 1920))
    canvas.snap_enabled = False
    item = canvas.add_widget("text", "test", position=QPointF(80, 160), width=200, height=100)
    canvas.set_canvas_size(3440, 1440)
    # Whole 480x1920 layout fits at 0.75, centered with 1540px left margin.
    assert (item.rect().width(), item.rect().height()) == (150, 75)
    assert (item.x(), item.y()) == (1600, 120)
    canvas._animation_timer.stop()
    canvas.deleteLater()


def test_resize_fits_inactive_pages_too(window):
    widget = WidgetConfig("text", 80, 160, 200, 100, "test")
    window._apply_profile(Profile(pages=[DashboardPage(widgets=[widget]), DashboardPage(widgets=[widget])]))
    window._resize_dashboard_canvas(3440, 1440, scale_widgets=True)
    window._switch_dashboard_page(1)
    item = window.canvas.widget_items()[0]
    assert (item.x(), item.y(), item.rect().width(), item.rect().height()) == (1600, 120, 150, 75)


def test_editor_fits_large_canvas_and_manual_zoom_survives_resize(window, app):
    window._resize_dashboard_canvas(3440, 1440, scale_widgets=False)
    app.processEvents()
    canvas = window.canvas
    visible = canvas.mapToScene(canvas.viewport().rect()).boundingRect()
    assert visible.contains(canvas.sceneRect())
    window._zoom_canvas(1.15)
    scale = canvas.transform().m11()
    window.resize(window.width() + 50, window.height() + 50)
    app.processEvents()
    assert canvas.transform().m11() == scale


def test_layout_does_not_shrink_again_after_save_and_switch_back(window):
    window.canvas.snap_enabled = False
    window._apply_profile(Profile(widgets=[WidgetConfig("text", 80, 160, 200, 100, "test")]))
    window._resize_dashboard_canvas(3440, 1440, scale_widgets=True)
    saved = window._profile_from_canvas().to_json()
    window._apply_profile(Profile.from_json(saved))
    window._resize_dashboard_canvas(480, 1920, scale_widgets=True)
    item = window.canvas.widget_items()[0]
    assert (item.x(), item.y(), item.rect().width(), item.rect().height()) == (80, 160, 200, 100)


def test_fitted_positions_survive_page_switch_and_reload_without_snapping(window):
    widget = WidgetConfig("text", 32, 180, 200, 100, "test")
    window._apply_profile(Profile(pages=[DashboardPage(widgets=[widget]), DashboardPage(widgets=[widget])]))
    window._resize_dashboard_canvas(3440, 1440, scale_widgets=True)
    window._switch_dashboard_page(1)
    assert window.canvas.widget_items()[0].x() == 1564
    saved = window._profile_from_canvas().to_json()
    window._apply_profile(Profile.from_json(saved))
    assert window.canvas.widget_items()[0].x() == 1564
