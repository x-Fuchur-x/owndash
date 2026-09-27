import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from owndash.core.models import BackgroundConfig
from owndash.core.preferences import AppPreferences
from owndash.gui.canvas import DashboardCanvas


def test_preferences_default_and_clamp_software_dimming():
    assert AppPreferences().software_dimming_percent == 100
    assert AppPreferences.from_raw({"software_dimming_percent": 5}).software_dimming_percent == 10
    assert AppPreferences.from_raw({"software_dimming_percent": 150}).software_dimming_percent == 100
    assert AppPreferences.from_raw({"software_dimming_percent": "50"}).software_dimming_percent == 50


def test_canvas_software_dimming_darkens_output_without_changing_100_percent():
    app = QApplication.instance() or QApplication([])
    canvas = DashboardCanvas()
    canvas.background_config = BackgroundConfig(mode="solid", color="#ffffff")

    full = QImage.fromData(canvas.render_jpeg(quality=95, software_dimming_percent=100))
    half = QImage.fromData(canvas.render_jpeg(quality=95, software_dimming_percent=50))

    assert not full.isNull()
    assert not half.isNull()
    full_pixel = full.pixelColor(full.width() // 2, full.height() // 2)
    half_pixel = half.pixelColor(half.width() // 2, half.height() // 2)
    assert full_pixel.red() >= 245
    assert 115 <= half_pixel.red() <= 140
    assert half_pixel.red() < full_pixel.red()

    canvas.close()
    app.processEvents()
