import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFormLayout

from owndash.core.display import DisplayCapabilities, DisplayInfo, DisplayProtocolError
from owndash.hardware.aic_usb import AicUsbDisplayBackend
from owndash.gui.display_controls import DisplayControlsWidget


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class RecordingBackend(AicUsbDisplayBackend):
    def __init__(self):
        super().__init__()
        self.caps = DisplayCapabilities(hardware_brightness=True)
        self.brightness = []
        self.failure = False

    def get_capabilities(self):
        return self.caps

    def set_brightness(self, percent):
        if self.failure:
            raise DisplayProtocolError("test failure")
        self.brightness.append(percent)


@pytest.fixture
def widget(app):
    backend = RecordingBackend()
    control = DisplayControlsWidget(backend, DisplayInfo("Test", 1920, 480))
    control.show()
    app.processEvents()
    yield control, backend
    control.close()
    control.deleteLater()
    app.processEvents()


def test_keyboard_brightness_reaches_backend(widget):
    control, backend = widget
    assert backend.brightness == []
    control.brightness_slider.setFocus()
    QTest.keyClick(control.brightness_slider, Qt.Key_Left)
    assert control.brightness_slider.value() == 99
    assert backend.brightness == [99]


def test_drag_defers_brightness_until_release(widget):
    control, backend = widget
    slider = control.brightness_slider
    slider.setSliderDown(True)
    slider.setValue(70)
    slider.setValue(50)
    assert backend.brightness == []
    slider.setSliderDown(False)
    assert backend.brightness == [50]


def test_unsupported_rows_hide_labels_and_fields(widget, app):
    control, backend = widget
    backend.caps = DisplayCapabilities()
    control.refresh_from_backend()
    app.processEvents()
    form = control.findChild(QFormLayout)
    for field in (control.version_label, control.brightness_slider.parentWidget()):
        assert not field.isVisible()
        assert not form.labelForField(field).isVisible()
    assert not control.expansion_check.isVisible()
    assert backend.brightness == []


def test_brightness_error_is_visible(widget):
    control, backend = widget
    backend.failure = True
    control.brightness_slider.setFocus()
    QTest.keyClick(control.brightness_slider, Qt.Key_Left)
    assert "test failure" in control.status_label.text()
    assert backend.brightness == []
