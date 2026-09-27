from __future__ import annotations

import getpass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
)

from owndash import __version__
from owndash.core.display import DisplayCapabilities, DisplayInfo
from owndash.core.preferences import save_preferences
from owndash.core.software_dimming import dim_jpeg
from owndash.service.device_diagnostics import (
    DeviceDiagnosticSnapshot,
    DeviceDiagnosticsService,
    format_diagnostic_report,
)

from .app_window import SafeShutdownWindow
from .display_controls import DeviceCenterWidget


_DEVICE_CENTER_EN: dict[str, str] = {
    "Geräteinformationen …": "Device Information …",
    "Geräteinformationen": "Device Information",
    "Software-Dimmung …": "Software dimming …",
    "Software-Dimmung": "Software dimming",
    "Die Ausgabe wird nur im Bild abgedunkelt. Die Hardware-Helligkeit des Displays wird nicht verändert.":
        "Only the image output is dimmed. The display hardware brightness is not changed.",
    "Ausgabe": "Output",
    "Ausgewählter Ausgang": "Selected output",
    "Aktiver Ausgang": "Active output",
    "Verbindung": "Connection",
    "Kein aktiver Ausgang": "No active output",
    "OwnDash-Funktionen": "OwnDash features",
    "OwnDash-Softwarefunktion": "OwnDash software feature",
    "Hardware-Funktionen": "Hardware capabilities",
    "Gerät": "Device",
    "USB & Zugriff": "USB & Access",
    "Funktionen": "Capabilities",
    "Letzte Aktivität": "Last activity",
    "Status": "Status",
    "Backend": "Backend",
    "Native Auflösung": "Native resolution",
    "Bildrate": "Refresh rate",
    "Ausgabemodus": "Output mode",
    "Rotation": "Rotation",
    "Erkannt": "Detected",
    "Zugriff": "Access",
    "Device-Node": "Device node",
    "udev-Regel": "udev rule",
    "Verbunden": "Connected",
    "Nicht verbunden": "Not connected",
    "Ja": "Yes",
    "Nein": "No",
    "Unbekannt": "Unknown",
    "Verfügbar": "Available",
    "Nicht unterstützt": "Unsupported",
    "Noch nicht verifiziert": "Not yet verified",
    "Zuletzt verbunden": "Last connected",
    "Zuletzt getrennt": "Last disconnected",
    "Zuletzt erkannt": "Last detected",
    "Letzter Fehler": "Last error",
    "Aktualisieren": "Refresh",
    "Diagnosebericht kopieren": "Copy diagnostic report",
    "JPEG-Ausgabe": "JPEG output",
    "Hardware-Helligkeit": "Hardware brightness",
    "Geräteversion": "Device version",
    "Panel-Informationen": "Panel information",
    "Expansion Screen Mode": "Expansion Screen Mode",
    "Startbild": "Startup image",
    "Startvideo": "Startup video",
    "Hardware-Bildschirm aus": "Hardware screen off",
    "Firmware-Aktualisierung": "Firmware upgrade",
    "Übernehmen": "Apply",
    "Abbrechen": "Cancel",
    "Schließen": "Close",
}

_BACKEND_NAMES = {
    "aic_usb": "ArtInChip / VSDISPLAY",
    "screen": "Standard-Monitor",
    "monitor": "Standard-Monitor",
}

_OUTPUT_MODES = {
    "aic_usb": "Direct USB",
    "screen": "Standard-Monitor",
    "monitor": "Standard-Monitor",
}


class DeviceCenterWindow(SafeShutdownWindow):
    """OwnDash main window with isolated diagnostics and safe display controls."""

    def _device_t(self, text: str) -> str:
        if getattr(self, "language", "de") == "en":
            return _DEVICE_CENTER_EN.get(text, self._t(text))
        return self._t(text)

    def _build_toolbar(self) -> None:
        super()._build_toolbar()
        self.device_center_action = self.display_controls_action
        self.device_center_action.setText(self._device_t("Geräteinformationen …"))
        self.device_center_action.setEnabled(True)

        self.software_dimming_action = QAction(self._device_t("Software-Dimmung …"), self)
        self.software_dimming_action.triggered.connect(self._open_software_dimming)
        for menu_action in self.menuBar().actions():
            menu = menu_action.menu()
            if menu is not None and menu_action.text().replace("&", "") == "Display":
                menu.insertSeparator(self.device_center_action)
                menu.insertAction(self.keep_running_action, self.software_dimming_action)
                menu.insertSeparator(self.keep_running_action)
                break

    def _retranslate_ui(self) -> None:
        super()._retranslate_ui()
        action = getattr(self, "device_center_action", None)
        if action is not None:
            action.setText(self._device_t("Geräteinformationen …"))
        dimming_action = getattr(self, "software_dimming_action", None)
        if dimming_action is not None:
            dimming_action.setText(self._device_t("Software-Dimmung …"))

    def __init__(self) -> None:
        super().__init__()
        self._device_diagnostics = DeviceDiagnosticsService()
        self.device_center_action.setEnabled(True)

    def _software_dim_frame(self, payload: bytes) -> bytes:
        return dim_jpeg(payload, self.preferences.software_dimming_percent)

    def _start_display_stream(self) -> None:
        super()._start_display_stream()
        streamer = self.display_streamer
        if streamer is not None:
            streamer.frame_transform = self._software_dim_frame

    def _refresh_output_after_dimming_change(self) -> None:
        self._last_display_payload = None
        refresh_state = getattr(self, "_refresh_visible_system_state", None)
        if callable(refresh_state):
            refresh_state()
        self._push_display_frame()

    def _open_software_dimming(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._device_t("Software-Dimmung"))
        dialog.setModal(True)
        dialog.setMinimumWidth(460)
        layout = QVBoxLayout(dialog)

        hint = QLabel(
            self._device_t(
                "Die Ausgabe wird nur im Bild abgedunkelt. Die Hardware-Helligkeit des Displays wird nicht verändert."
            ),
            dialog,
        )
        hint.setWordWrap(True)
        hint.setMinimumHeight(hint.fontMetrics().lineSpacing() * 2 + 8)
        layout.addWidget(hint)

        row = QHBoxLayout()
        slider = QSlider(Qt.Horizontal, dialog)
        slider.setObjectName("softwareDimmingSlider")
        slider.setRange(10, 100)
        slider.setSingleStep(5)
        slider.setPageStep(10)
        slider.setValue(int(self.preferences.software_dimming_percent))
        value_label = QLabel(f"{slider.value()} %", dialog)
        value_label.setObjectName("softwareDimmingValue")
        value_label.setMinimumWidth(52)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        layout.addLayout(row)

        original = int(self.preferences.software_dimming_percent)

        def preview(value: int) -> None:
            self.preferences.software_dimming_percent = int(value)
            value_label.setText(f"{value} %")
            self._refresh_output_after_dimming_change()

        slider.valueChanged.connect(preview)

        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel, dialog)
        apply_button = buttons.button(QDialogButtonBox.Apply)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if apply_button is not None:
            apply_button.setText(self._device_t("Übernehmen"))
            apply_button.clicked.connect(dialog.accept)
        if cancel_button is not None:
            cancel_button.setText(self._device_t("Abbrechen"))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            self.preferences.software_dimming_percent = int(slider.value())
            save_preferences(self.preferences)
        else:
            self.preferences.software_dimming_percent = original
            self._refresh_output_after_dimming_change()

    def _display_connected(self, info: object) -> None:
        super()._display_connected(info)
        if isinstance(info, DisplayInfo):
            self._device_diagnostics.record_connected(info)
        self.device_center_action.setEnabled(True)

    def _stop_display_stream(self) -> None:
        was_connected = bool(
            getattr(self, "display_connected", False)
            or getattr(self, "_connected_display_info", None) is not None
        )
        if was_connected and hasattr(self, "_device_diagnostics"):
            self._device_diagnostics.record_disconnected()
        super()._stop_display_stream()
        if hasattr(self, "device_center_action"):
            self.device_center_action.setEnabled(True)

    def _display_error(self, error: object) -> None:
        was_connected = bool(
            getattr(self, "display_connected", False)
            or getattr(self, "_connected_display_info", None) is not None
        )
        diagnostics = getattr(self, "_device_diagnostics", None)
        if diagnostics is not None:
            diagnostics.record_error(error)
            if was_connected:
                diagnostics.record_disconnected()
        super()._display_error(error)
        if hasattr(self, "device_center_action"):
            self.device_center_action.setEnabled(True)

    def _device_diagnostic_snapshot(self) -> DeviceDiagnosticSnapshot:
        streamer = getattr(self, "display_streamer", None)
        capabilities = DisplayCapabilities()
        if streamer is not None:
            backend = getattr(streamer, "backend", None)
            if backend is not None:
                try:
                    capabilities = backend.get_capabilities()
                except Exception:
                    capabilities = DisplayCapabilities()

        backend_key = str(getattr(self, "display_backend_key", "") or "unknown")
        backend_name = _BACKEND_NAMES.get(backend_key, backend_key)
        output_mode = _OUTPUT_MODES.get(backend_key, backend_name)
        connected = bool(getattr(self, "display_connected", False))
        info = getattr(self, "_connected_display_info", None)
        current_info = info if connected and isinstance(info, DisplayInfo) else None

        rotation = getattr(self, "_display_rotation", None)
        if rotation is None and streamer is not None:
            backend = getattr(streamer, "backend", None)
            settings = getattr(backend, "settings", None)
            candidate = getattr(settings, "rotation", None)
            if isinstance(candidate, int):
                rotation = candidate

        return self._device_diagnostics.snapshot(
            backend_key=backend_key,
            backend_name=backend_name,
            connected=connected,
            current_info=current_info,
            capabilities=capabilities,
            output_mode=output_mode,
            rotation=rotation,
        )

    def _device_diagnostic_report(self, snapshot: DeviceDiagnosticSnapshot) -> str:
        system_info: dict[str, str] = {}
        try:
            diagnostics = self.sensor_provider.diagnostics()
            raw_system = diagnostics.get("system", {}) if isinstance(diagnostics, dict) else {}
            if isinstance(raw_system, dict):
                system_info = {
                    key: str(raw_system[key])
                    for key in ("distribution", "kernel", "desktop", "session")
                    if raw_system.get(key)
                }
        except Exception:
            system_info = {}

        try:
            username = getpass.getuser()
        except Exception:
            username = None
        try:
            home = str(Path.home())
        except Exception:
            home = None

        return format_diagnostic_report(
            snapshot,
            app_version=__version__,
            system_info=system_info,
            home=home,
            username=username,
        )

    def _open_device_center(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self._device_t("Geräteinformationen"))
        dialog.setModal(True)
        dialog.setMinimumSize(620, 560)
        dialog.resize(680, 640)

        layout = QVBoxLayout(dialog)
        controls = DeviceCenterWidget(
            self._device_diagnostic_snapshot(),
            refresh_snapshot=self._device_diagnostic_snapshot,
            report_text=self._device_diagnostic_report,
            translate=self._device_t,
            software_dimming_percent=self.preferences.software_dimming_percent,
        )

        controls.refresh_button.hide()
        controls.copy_button.hide()
        controls.refresh_button.setObjectName("deviceCenterEmbeddedRefreshButton")
        controls.copy_button.setObjectName("deviceCenterEmbeddedCopyButton")

        scroll = QScrollArea(dialog)
        scroll.setObjectName("deviceCenterScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(controls)
        layout.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)

        refresh_button = QPushButton(self._device_t("Aktualisieren"), dialog)
        refresh_button.setObjectName("deviceCenterRefreshButton")
        refresh_button.clicked.connect(controls.refresh_button.click)
        footer.addWidget(refresh_button)

        copy_button = QPushButton(self._device_t("Diagnosebericht kopieren"), dialog)
        copy_button.setObjectName("deviceCenterCopyButton")
        copy_button.clicked.connect(controls.copy_button.click)
        footer.addWidget(copy_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._device_t("Schließen"))
        buttons.rejected.connect(dialog.reject)
        footer.addWidget(buttons)
        layout.addLayout(footer)
        dialog.exec()

    def _open_display_controls(self) -> None:
        """Compatibility target for the existing Display-menu action."""
        self._open_device_center()
