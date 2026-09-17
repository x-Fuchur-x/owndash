from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from owndash.core.display import DisplayBackend, DisplayCapabilities, DisplayInfo, DisplayProtocolError
from owndash.gui.display_controls import DisplayControlsWidget


class FakeBackend(DisplayBackend):
    def __init__(self, caps: DisplayCapabilities, *, fail: bool = False):
        self.caps = caps
        self.fail = fail
        self.brightness_calls: list[int] = []
        self.expansion_calls: list[bool] = []

    def connect(self) -> DisplayInfo:
        return DisplayInfo("Fake", 480, 1920)

    def send_jpeg(self, payload: bytes) -> None:
        pass

    def close(self) -> None:
        pass

    def get_capabilities(self) -> DisplayCapabilities:
        return self.caps

    def get_device_version(self) -> str | None:
        return "1.2.3"

    def get_expansion_mode(self) -> bool | None:
        return True

    def set_brightness(self, percent: int) -> None:
        if self.fail:
            raise DisplayProtocolError("boom")
        self.brightness_calls.append(percent)

    def set_expansion_mode(self, enabled: bool) -> None:
        if self.fail:
            raise DisplayProtocolError("boom")
        self.expansion_calls.append(enabled)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_controls_show_supported_device_data_and_delegate_changes():
    _app()
    backend = FakeBackend(DisplayCapabilities(hardware_brightness=True, device_version=True, expansion_mode=True))
    info = DisplayInfo("USB Bar Display", 480, 1920, device_version="1.2.3", expansion_mode=True)
    widget = DisplayControlsWidget(backend, info)
    assert "480×1920" in widget.device_label.text()
    assert widget.version_label.text() == "1.2.3"
    assert widget.brightness_slider.parentWidget().isHidden() is False
    assert widget.expansion_check.isHidden() is False

    widget.brightness_slider.setValue(50)
    widget.brightness_slider.sliderReleased.emit()
    assert backend.brightness_calls == [50]

    widget.expansion_check.setChecked(False)
    assert backend.expansion_calls == [False]


def test_unsupported_controls_are_hidden():
    _app()
    backend = FakeBackend(DisplayCapabilities())
    widget = DisplayControlsWidget(backend, DisplayInfo("Screen", 1920, 1080))
    assert widget.brightness_slider.parentWidget().isHidden() is True
    assert widget.expansion_check.isHidden() is True
    assert widget.version_label.isHidden() is True


def test_control_errors_are_non_fatal_status_text():
    _app()
    backend = FakeBackend(DisplayCapabilities(hardware_brightness=True), fail=True)
    widget = DisplayControlsWidget(backend, DisplayInfo("USB", 480, 1920))
    widget.brightness_slider.setValue(25)
    widget.brightness_slider.sliderReleased.emit()
    assert "boom" in widget.status_label.text()
