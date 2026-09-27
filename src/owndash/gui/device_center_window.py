from __future__ import annotations

import getpass
from pathlib import Path

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from owndash import __version__
from owndash.core.display import DisplayCapabilities, DisplayInfo
from owndash.service.device_diagnostics import (
    DeviceDiagnosticSnapshot,
    DeviceDiagnosticsService,
    format_diagnostic_report,
)

from .app_window import SafeShutdownWindow
from .display_controls import DeviceCenterWidget


_DEVICE_CENTER_EN: dict[str, str] = {
    "Display & Gerät …": "Display & Device …",
    "Display & Gerät": "Display & Device",
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
    """OwnDash main window with isolated, read-only device diagnostics.

    Keeping this integration in its own thin subclass avoids adding another
    responsibility to the already sizeable SafeShutdownWindow while preserving
    all of its shutdown, suspend/resume and system-state behavior unchanged.
    """

    def _device_t(self, text: str) -> str:
        if getattr(self, "language", "de") == "en":
            return _DEVICE_CENTER_EN.get(text, self._t(text))
        return self._t(text)

    def _build_toolbar(self) -> None:
        # The base class creates the existing Display menu slot. Reuse it so
        # menu order and shortcuts remain stable, but broaden its purpose and
        # keep it available even when no hardware is connected.
        super()._build_toolbar()
        self.device_center_action = self.display_controls_action
        self.device_center_action.setText(self._device_t("Display & Gerät …"))
        self.device_center_action.setEnabled(True)

    def _retranslate_ui(self) -> None:
        # MainWindow retranslates its canonical UI tree. Device Center copy is
        # intentionally isolated here, so refresh the reused Display action
        # after every runtime language change as well as during startup.
        super()._retranslate_ui()
        action = getattr(self, "device_center_action", None)
        if action is not None:
            action.setText(self._device_t("Display & Gerät …"))

    def __init__(self) -> None:
        super().__init__()
        self._device_diagnostics = DeviceDiagnosticsService()
        self.device_center_action.setEnabled(True)

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
                    # Diagnostics must never turn a backend read failure into a
                    # modal app failure or an attempted reconnect.
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
        dialog.setWindowTitle(self._device_t("Display & Gerät"))
        dialog.setModal(True)
        dialog.setMinimumSize(620, 560)
        dialog.resize(680, 640)

        layout = QVBoxLayout(dialog)
        controls = DeviceCenterWidget(
            self._device_diagnostic_snapshot(),
            refresh_snapshot=self._device_diagnostic_snapshot,
            report_text=self._device_diagnostic_report,
            parent=dialog,
            translate=self._device_t,
        )
        layout.addWidget(controls, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._device_t("Schließen"))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _open_display_controls(self) -> None:
        """Compatibility target for the existing Display-menu action."""
        self._open_device_center()
