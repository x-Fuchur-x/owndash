from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QLabel, QSlider, QVBoxLayout, QWidget

from owndash.core.display import DisplayBackend, DisplayInfo, DisplayProtocolError


class DisplayControlsWidget(QWidget):
    """Capability-driven controls for an already connected display backend."""

    def __init__(
        self,
        backend: DisplayBackend,
        info: DisplayInfo,
        parent: QWidget | None = None,
        *,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.backend = backend
        self.info = info
        self._t = translate or (lambda text: text)
        self._refreshing = False

        outer = QVBoxLayout(self)
        form = QFormLayout()
        self._form = form
        outer.addLayout(form)

        self.device_label = QLabel(f"{info.name} · {info.width}×{info.height}", self)
        self.device_label.setObjectName("displayDeviceInfo")
        self.device_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow(self._t("Gerät"), self.device_label)

        self.version_label = QLabel("—", self)
        self.version_label.setObjectName("displayDeviceVersion")
        self.version_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow(self._t("Geräteversion"), self.version_label)

        self.brightness_slider = QSlider(Qt.Horizontal, self)
        self.brightness_slider.setObjectName("displayBrightnessSlider")
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(100)
        self.brightness_value = QLabel("100 %", self)
        self.brightness_slider.valueChanged.connect(lambda value: self.brightness_value.setText(f"{value} %"))
        self.brightness_slider.valueChanged.connect(self._brightness_changed)
        self.brightness_slider.sliderReleased.connect(self._apply_brightness)
        brightness_row = QWidget(self)
        brightness_layout = QVBoxLayout(brightness_row)
        brightness_layout.setContentsMargins(0, 0, 0, 0)
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_value)
        form.addRow(self._t("Helligkeit"), brightness_row)

        self.expansion_check = QCheckBox(self._t("Expansion Screen Mode"), self)
        self.expansion_check.setObjectName("displayExpansionMode")
        self.expansion_check.toggled.connect(self._apply_expansion_mode)
        form.addRow("", self.expansion_check)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("displayControlStatus")
        self.status_label.setWordWrap(True)
        outer.addWidget(self.status_label)

        self.refresh_from_backend()

    def refresh_from_backend(self) -> None:
        caps = self.backend.get_capabilities()
        self._form.setRowVisible(self.brightness_slider.parentWidget(), caps.hardware_brightness)
        self._form.setRowVisible(self.expansion_check, caps.expansion_mode)
        self._form.setRowVisible(self.version_label, caps.device_version)

        self._refreshing = True
        try:
            if caps.device_version:
                version = self.info.device_version
                if version is None:
                    try:
                        version = self.backend.get_device_version()
                    except DisplayProtocolError as exc:
                        self._show_error(exc)
                self.version_label.setText(version or "—")

            if caps.expansion_mode:
                state = self.info.expansion_mode
                if state is None:
                    try:
                        state = self.backend.get_expansion_mode()
                    except DisplayProtocolError as exc:
                        self._show_error(exc)
                if state is not None:
                    self.expansion_check.setChecked(bool(state))
        finally:
            self._refreshing = False

    def _brightness_changed(self, value: int) -> None:
        # Keyboard, wheel and groove clicks do not emit sliderReleased.
        # Dragging still sends only once, when the handle is released.
        if not self.brightness_slider.isSliderDown():
            self._apply_brightness()

    def _apply_brightness(self) -> None:
        if self._refreshing or not self.backend.get_capabilities().hardware_brightness:
            return
        try:
            self.backend.set_brightness(int(self.brightness_slider.value()))
            self.status_label.setText("")
        except DisplayProtocolError as exc:
            self._show_error(exc)

    def _apply_expansion_mode(self, enabled: bool) -> None:
        if self._refreshing:
            return
        try:
            self.backend.set_expansion_mode(bool(enabled))
            self.status_label.setText("")
        except DisplayProtocolError as exc:
            self._show_error(exc)

    def _show_error(self, error: Exception) -> None:
        self.status_label.setText(self._t("Display-Steuerung nicht verfügbar") + f": {error}")
