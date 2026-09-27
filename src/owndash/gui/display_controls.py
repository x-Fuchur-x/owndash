from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from owndash.service.device_diagnostics import (
    CapabilityStatus,
    DeviceDiagnosticSnapshot,
)


_CAPABILITY_TITLES = {
    "jpeg_streaming": "JPEG-Ausgabe",
    "hardware_brightness": "Hardware-Helligkeit",
    "device_version": "Geräteversion",
    "panel_info": "Panel-Informationen",
    "expansion_mode": "Expansion Screen Mode",
    "startup_image": "Startbild",
    "startup_video": "Startvideo",
    "hardware_screen_off": "Hardware-Bildschirm aus",
    "firmware_upgrade": "Firmware-Aktualisierung",
}

_CAPABILITY_STATUS_TEXT = {
    CapabilityStatus.AVAILABLE: "Verfügbar",
    CapabilityStatus.UNSUPPORTED: "Nicht unterstützt",
    CapabilityStatus.UNVERIFIED: "Noch nicht verifiziert",
}


def _format_time(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value is not None else "—"


def _yes_no_unknown(value: bool | None, translate: Callable[[str], str]) -> str:
    if value is None:
        return translate("Unbekannt")
    return translate("Ja") if value else translate("Nein")


class DeviceCenterWidget(QWidget):
    """Read-only view of current and last-known display diagnostics."""

    def __init__(
        self,
        snapshot: DeviceDiagnosticSnapshot,
        *,
        refresh_snapshot: Callable[[], DeviceDiagnosticSnapshot],
        report_text: Callable[[DeviceDiagnosticSnapshot], str],
        parent: QWidget | None = None,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._t = translate or (lambda text: text)
        self._refresh_snapshot = refresh_snapshot
        self._report_text = report_text
        self._snapshot = snapshot
        self._capability_labels: dict[str, QLabel] = {}
        self._capability_name_labels: list[QLabel] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        self.device_section = QGroupBox(self._t("Gerät"), self)
        self.device_section.setObjectName("deviceCenterDeviceSection")
        self.device_form = QFormLayout(self.device_section)
        self.connection_status_label = self._value_label("deviceCenterConnectionStatus")
        self.backend_label = self._value_label("deviceCenterBackend")
        self.device_name_label = self._value_label("deviceCenterDeviceName")
        self.native_label = self._value_label("deviceCenterNativeResolution")
        self.refresh_label = self._value_label("deviceCenterRefreshRate")
        self.output_label = self._value_label("deviceCenterOutputMode")
        self.rotation_label = self._value_label("deviceCenterRotation")
        self.device_form.addRow(self._t("Status"), self.connection_status_label)
        self.device_form.addRow(self._t("Backend"), self.backend_label)
        self.device_form.addRow(self._t("Gerät"), self.device_name_label)
        self.device_form.addRow(self._t("Native Auflösung"), self.native_label)
        self.device_form.addRow(self._t("Bildrate"), self.refresh_label)
        self.device_form.addRow(self._t("Ausgabemodus"), self.output_label)
        self.device_form.addRow(self._t("Rotation"), self.rotation_label)
        outer.addWidget(self.device_section)

        self.usb_section = QGroupBox(self._t("USB & Zugriff"), self)
        self.usb_section.setObjectName("deviceCenterUsbSection")
        self.usb_form = QFormLayout(self.usb_section)
        self.vid_pid_label = self._value_label("deviceCenterUsbId")
        self.detected_label = self._value_label("deviceCenterUsbDetected")
        self.access_label = self._value_label("deviceCenterUsbAccess")
        self.device_node_label = self._value_label("deviceCenterDeviceNode")
        self.udev_label = self._value_label("deviceCenterUdevState")
        self.usb_form.addRow("VID:PID", self.vid_pid_label)
        self.usb_form.addRow(self._t("Erkannt"), self.detected_label)
        self.usb_form.addRow(self._t("Zugriff"), self.access_label)
        self.usb_form.addRow(self._t("Device-Node"), self.device_node_label)
        self.usb_form.addRow(self._t("udev-Regel"), self.udev_label)
        outer.addWidget(self.usb_section)

        self.capabilities_section = QGroupBox(self._t("Funktionen"), self)
        self.capabilities_section.setObjectName("deviceCenterCapabilitiesSection")
        self.capabilities_form = QFormLayout(self.capabilities_section)
        outer.addWidget(self.capabilities_section)

        self.activity_section = QGroupBox(self._t("Letzte Aktivität"), self)
        self.activity_section.setObjectName("deviceCenterActivitySection")
        self.activity_form = QFormLayout(self.activity_section)
        self.last_connected_label = self._value_label("deviceCenterLastConnected")
        self.last_disconnected_label = self._value_label("deviceCenterLastDisconnected")
        self.last_known_label = self._value_label("deviceCenterLastKnown")
        self.last_error_label = self._value_label("deviceCenterLastError")
        self.last_error_label.setWordWrap(True)
        self.activity_form.addRow(self._t("Zuletzt verbunden"), self.last_connected_label)
        self.activity_form.addRow(self._t("Zuletzt getrennt"), self.last_disconnected_label)
        self.activity_form.addRow(self._t("Zuletzt erkannt"), self.last_known_label)
        self.activity_form.addRow(self._t("Letzter Fehler"), self.last_error_label)
        outer.addWidget(self.activity_section)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.refresh_button = QPushButton(self._t("Aktualisieren"), self)
        self.refresh_button.setObjectName("deviceCenterRefreshButton")
        self.refresh_button.clicked.connect(self._refresh)
        footer.addWidget(self.refresh_button)
        self.copy_button = QPushButton(self._t("Diagnosebericht kopieren"), self)
        self.copy_button.setObjectName("deviceCenterCopyButton")
        self.copy_button.clicked.connect(self._copy_report)
        footer.addWidget(self.copy_button)
        outer.addLayout(footer)

        self.set_snapshot(snapshot)

    def _value_label(self, object_name: str) -> QLabel:
        label = QLabel("—", self)
        label.setObjectName(object_name)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def set_snapshot(self, snapshot: DeviceDiagnosticSnapshot) -> None:
        self._snapshot = snapshot
        self.connection_status_label.setText(
            self._t("Verbunden") if snapshot.connected else self._t("Nicht verbunden")
        )
        self.backend_label.setText(
            f"{snapshot.backend_name} ({snapshot.backend_key})"
            if snapshot.backend_name
            else snapshot.backend_key or "—"
        )
        self.device_name_label.setText(snapshot.device_name or "—")
        if snapshot.native_width is not None and snapshot.native_height is not None:
            self.native_label.setText(f"{snapshot.native_width}×{snapshot.native_height}")
        else:
            self.native_label.setText("—")
        self.refresh_label.setText(
            f"{snapshot.refresh_hz} Hz" if snapshot.refresh_hz is not None else "—"
        )
        self.output_label.setText(snapshot.output_mode or "—")
        self.rotation_label.setText(
            f"{snapshot.rotation}°" if snapshot.rotation is not None else "—"
        )

        self.vid_pid_label.setText(snapshot.usb_vid_pid or "—")
        self.detected_label.setText(_yes_no_unknown(snapshot.device_detected, self._t))
        self.access_label.setText(_yes_no_unknown(snapshot.accessible, self._t))
        self.device_node_label.setText(snapshot.device_node or "—")
        self.udev_label.setText(snapshot.udev_state or "unknown")

        self._rebuild_capabilities(snapshot)

        self.last_connected_label.setText(_format_time(snapshot.last_connected_at))
        self.last_disconnected_label.setText(_format_time(snapshot.last_disconnected_at))
        if snapshot.last_known_info is not None:
            info = snapshot.last_known_info
            self.last_known_label.setText(f"{info.name} · {info.width}×{info.height}")
        else:
            self.last_known_label.setText("—")
        if snapshot.last_error_message:
            if snapshot.last_error_category is not None:
                self.last_error_label.setText(
                    f"{snapshot.last_error_category.value}: {snapshot.last_error_message}"
                )
            else:
                self.last_error_label.setText(snapshot.last_error_message)
        else:
            self.last_error_label.setText("—")

    def _rebuild_capabilities(self, snapshot: DeviceDiagnosticSnapshot) -> None:
        while self.capabilities_form.rowCount():
            self.capabilities_form.removeRow(0)
        self._capability_labels.clear()
        self._capability_name_labels.clear()

        for item in snapshot.capabilities:
            title = self._t(_CAPABILITY_TITLES.get(item.key, item.key))
            name_label = QLabel(title, self.capabilities_section)
            status_label = QLabel(self._t(_CAPABILITY_STATUS_TEXT[item.status]), self.capabilities_section)
            status_label.setObjectName(f"deviceCenterCapability_{item.key}")
            status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.capabilities_form.addRow(name_label, status_label)
            self._capability_name_labels.append(name_label)
            self._capability_labels[item.key] = status_label

    def _refresh(self) -> None:
        try:
            snapshot = self._refresh_snapshot()
        except Exception as exc:
            self.last_error_label.setText(str(exc))
            return
        self.set_snapshot(snapshot)

    def _copy_report(self) -> None:
        report = self._report_text(self._snapshot)
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(report)


# Temporary compatibility name while SafeShutdownWindow is migrated to the
# broader Device Center in the next integration step.
DisplayControlsWidget = DeviceCenterWidget
