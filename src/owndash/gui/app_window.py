from __future__ import annotations

from threading import Thread
import webbrowser

from PySide6.QtCore import QBuffer, QByteArray, QObject, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QImage, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSystemTrayIcon,
    QVBoxLayout,
)

from owndash import APP_NAME, __version__
from owndash.assets import app_icon_path
from owndash.appearance import apply_appearance
from owndash.core.preferences import save_preferences
from owndash.core.system_state import SystemState
from owndash.core.updates import ReleaseInfo, fetch_available_update
from owndash.i18n import resolved_language
from owndash.service.idle_state import IdleStateMonitor
from owndash.service.system_state_linux import LinuxSystemStateAdapter
from owndash.service.system_state_runtime import SystemStateRuntime

from .display_controls import DisplayControlsWidget
from .main_window import MainWindow
from .system_state_frame import render_system_state_image
from .system_state_settings import SystemStateSettingsWidget


class UpdateBridge(QObject):
    """Marshal background update results safely back onto the Qt GUI thread."""

    completed = Signal(object)


class SafeShutdownWindow(MainWindow):
    """OwnDash lifecycle extensions for shutdown, updates and system states."""

    def _build_toolbar(self) -> None:
        super()._build_toolbar()
        self.display_controls_action = QAction(self._t("Display-Steuerung …"), self)
        self.display_controls_action.setEnabled(False)
        self.display_controls_action.triggered.connect(self._open_display_controls)
        for action in self.menuBar().actions():
            menu = action.menu()
            if menu is not None and action.text().replace("&", "") == "Display":
                menu.insertAction(self.keep_running_action, self.display_controls_action)
                break

    def __init__(self):
        super().__init__()
        self._connected_display_info = None

        # System-state screens are deliberately event-driven. While one is
        # visible, OwnDash stops its periodic sensor/display/page timers and
        # sends one static frame only. This keeps lock/idle/suspend overhead as
        # close to zero as the Qt event loop permits.
        self._system_state_paused = False
        self._system_state_live_was_active = False
        self._system_state_display_was_active = False
        self._system_state_page_cycle_was_active = False
        self._system_state_runtime = SystemStateRuntime(
            self._show_system_state,
            self._restore_dashboard_after_system_state,
            lock_enabled=self.preferences.lock_screen_state,
            idle_enabled=self.preferences.idle_mode,
        )
        self._system_state_adapter = LinuxSystemStateAdapter(parent=self)
        self._system_state_adapter.condition_changed.connect(
            self._handle_system_state_condition
        )
        self._idle_state_monitor = IdleStateMonitor(
            timeout_seconds=self.preferences.idle_timeout_minutes * 60,
            enabled=self.preferences.idle_mode,
            parent=self,
        )
        self._idle_state_monitor.idle_changed.connect(
            lambda idle: self._handle_system_state_condition(SystemState.IDLE, idle)
        )
        self._apply_system_state_preferences()

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._stop_system_state_services)

        self._update_bridge = UpdateBridge(self)
        self._update_bridge.completed.connect(self._handle_update_result)
        self._update_check_started = False
        self._update_dialog: QMessageBox | None = None
        self._schedule_update_check()

    def _display_connected(self, info: object) -> None:
        super()._display_connected(info)
        self._connected_display_info = info
        streamer = self.display_streamer
        caps = streamer.backend.get_capabilities() if streamer is not None else None
        if hasattr(self, "display_controls_action"):
            self.display_controls_action.setEnabled(
                bool(caps and (caps.hardware_brightness or caps.device_version or caps.expansion_mode))
            )

        runtime = getattr(self, "_system_state_runtime", None)
        if runtime is not None and runtime.visible_state is not SystemState.ACTIVE:
            # A display may finish connecting while the desktop is already
            # locked/idle. Never flash a normal dashboard in that situation.
            self._system_state_display_was_active = True
            self.display_timer.stop()
            self._send_system_state_frame(runtime.visible_state)

    def _push_display_frame(self) -> None:
        runtime = getattr(self, "_system_state_runtime", None)
        if runtime is not None and runtime.visible_state is not SystemState.ACTIVE:
            return
        super()._push_display_frame()

    def _prepare_display_switch(self) -> None:
        if self.display_backend_key == "aic_usb":
            self.display_timer.stop()
            self._show_shutdown_frame(reason="switch")

    def _stop_display_stream(self) -> None:
        self._connected_display_info = None
        if hasattr(self, "display_controls_action"):
            self.display_controls_action.setEnabled(False)
        super()._stop_display_stream()

    def _display_error(self, error: object) -> None:
        self._connected_display_info = None
        if hasattr(self, "display_controls_action"):
            self.display_controls_action.setEnabled(False)
        super()._display_error(error)

    def _open_display_controls(self) -> None:
        streamer = self.display_streamer
        info = self._connected_display_info
        if streamer is None or info is None or not self.display_connected:
            QMessageBox.information(
                self,
                self._t("Display-Steuerung"),
                self._t("Die Display-Steuerung ist erst nach erfolgreicher Verbindung verfügbar."),
            )
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("Display-Steuerung"))
        dialog.setModal(True)
        dialog.setMinimumWidth(460)
        layout = QVBoxLayout(dialog)
        controls = DisplayControlsWidget(streamer.backend, info, dialog, translate=self._t)
        layout.addWidget(controls)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(self._t("Schließen"))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _schedule_update_check(self) -> None:
        if not self.preferences.check_updates:
            return
        QTimer.singleShot(1500, self._start_update_check)

    def _start_update_check(self) -> None:
        if not self.preferences.check_updates or self._update_check_started:
            return
        self._update_check_started = True

        def check() -> None:
            release = fetch_available_update(__version__)
            self._update_bridge.completed.emit(release)

        Thread(target=check, name="OwnDash-UpdateCheck", daemon=True).start()

    def _handle_update_result(self, release: object) -> None:
        if isinstance(release, ReleaseInfo):
            self._show_update_available(release)

    def _show_update_available(self, release: ReleaseInfo) -> None:
        if self._update_dialog is not None:
            return

        german = self.language == "de"
        dialog = QMessageBox(self)
        dialog.setWindowTitle("OwnDash-Update verfügbar" if german else "OwnDash update available")
        dialog.setIcon(QMessageBox.Information)
        dialog.setText(
            "Eine neue OwnDash-Version ist verfügbar."
            if german
            else "A new OwnDash version is available."
        )
        dialog.setInformativeText(
            f"Installiert: {__version__}\nVerfügbar: {release.tag}"
            if german
            else f"Installed: {__version__}\nAvailable: {release.tag}"
        )
        dialog.setStandardButtons(QMessageBox.NoButton)
        open_button = dialog.addButton(
            "Release-Seite öffnen" if german else "Open release page",
            QMessageBox.AcceptRole,
        )
        dialog.addButton("Später" if german else "Later", QMessageBox.RejectRole)
        open_button.clicked.connect(lambda: webbrowser.open(release.url))
        dialog.finished.connect(self._clear_update_dialog)
        dialog.setModal(False)
        self._update_dialog = dialog
        dialog.show()

    def _clear_update_dialog(self, _result: int) -> None:
        dialog = self._update_dialog
        self._update_dialog = None
        if dialog is not None:
            dialog.deleteLater()

    def _open_settings(self) -> None:
        """Show general, update and system-state settings."""
        was_checking_updates = self.preferences.check_updates

        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("Einstellungen"))
        dialog.setModal(True)
        dialog.setMinimumWidth(440)

        outer = QVBoxLayout(dialog)
        form = QFormLayout()
        self._polish_form(form)

        language_combo = QComboBox(dialog)
        language_combo.addItem(self._t("Systemsprache"), "system")
        language_combo.addItem(self._t("Deutsch"), "de")
        language_combo.addItem(self._t("Englisch"), "en")
        language_index = language_combo.findData(self.preferences.language)
        language_combo.setCurrentIndex(max(0, language_index))

        appearance_combo = QComboBox(dialog)
        appearance_combo.addItem(self._t("System"), "system")
        appearance_combo.addItem(self._t("Dunkel"), "dark")
        appearance_combo.addItem(self._t("Hell"), "light")
        appearance_index = appearance_combo.findData(self.preferences.appearance)
        appearance_combo.setCurrentIndex(max(0, appearance_index))

        form.addRow(self._t("Sprache"), language_combo)
        form.addRow(self._t("Erscheinungsbild"), appearance_combo)
        outer.addLayout(form)

        if self.language == "de":
            update_label = "Automatisch nach Updates suchen"
            update_explanation = (
                "OwnDash prüft gelegentlich auf GitHub nach neuen Versionen. "
                "Es wird nichts automatisch heruntergeladen oder installiert."
            )
        else:
            update_label = "Automatically check for updates"
            update_explanation = (
                "OwnDash occasionally checks GitHub for new versions. "
                "Nothing is downloaded or installed automatically."
            )

        update_check = QCheckBox(update_label, dialog)
        update_check.setChecked(self.preferences.check_updates)
        outer.addWidget(update_check)

        update_hint = QLabel(update_explanation, dialog)
        update_hint.setWordWrap(True)
        outer.addWidget(update_hint)

        system_state_settings = SystemStateSettingsWidget(
            self.preferences,
            dialog,
            translate=self._t,
        )
        outer.addWidget(system_state_settings)

        hint = QLabel(self._t("Sprache und Erscheinungsbild werden sofort angewendet."), dialog)
        hint.setWordWrap(True)
        outer.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel, dialog)
        apply_button = buttons.button(QDialogButtonBox.Apply)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if apply_button is not None:
            apply_button.setText(self._t("Übernehmen"))
            apply_button.clicked.connect(dialog.accept)
        if cancel_button is not None:
            cancel_button.setText(self._t("Abbrechen"))
        buttons.rejected.connect(dialog.reject)
        outer.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        self.preferences.language = str(language_combo.currentData())
        self.preferences.appearance = str(appearance_combo.currentData())
        self.preferences.check_updates = update_check.isChecked()
        system_state_settings.apply_to(self.preferences)
        save_preferences(self.preferences)

        self.language = resolved_language(self.preferences.language)
        apply_appearance(self.preferences.appearance, self._system_palette)
        self._apply_ui_polish()
        self._retranslate_ui()
        self._apply_system_state_preferences()
        self._refresh_visible_system_state()
        self.statusBar().showMessage(self._t("Bereit · Live-Vorschau aktiv"), 2500)

        if self.preferences.check_updates and not was_checking_updates:
            self._schedule_update_check()

    def _apply_system_state_preferences(self) -> None:
        """Apply preferences without adding any periodic polling."""
        master = bool(self.preferences.system_state_screens)
        idle_enabled = master and bool(self.preferences.idle_mode)
        lock_enabled = master and bool(self.preferences.lock_screen_state)

        self._idle_state_monitor.set_timeout_seconds(
            int(self.preferences.idle_timeout_minutes) * 60
        )
        self._idle_state_monitor.set_enabled(idle_enabled)

        if not master:
            self._system_state_adapter.stop()
            self._idle_state_monitor.stop()
            if self._system_state_runtime.visible_state is not SystemState.ACTIVE:
                self._restore_dashboard_after_system_state()
            # Dropping the old coordinator also drops any stale suspend/terminal
            # condition that may never receive its matching end event while the
            # feature is disabled.
            self._system_state_runtime = SystemStateRuntime(
                self._show_system_state,
                self._restore_dashboard_after_system_state,
                lock_enabled=False,
                idle_enabled=False,
            )
            return

        self._system_state_runtime.configure(
            lock_enabled=lock_enabled,
            idle_enabled=idle_enabled,
        )
        self._system_state_adapter.start()
        if idle_enabled:
            self._idle_state_monitor.start()
        else:
            self._idle_state_monitor.stop()

    def _handle_system_state_condition(self, state: SystemState, enabled: bool) -> None:
        if not self.preferences.system_state_screens:
            return
        if not isinstance(state, SystemState):
            return
        self._system_state_runtime.handle_condition(state, bool(enabled))

    def _render_system_state_payload(self, state: SystemState) -> bytes | None:
        if state is SystemState.ACTIVE:
            return None
        with app_icon_path() as icon_path:
            icon = QIcon(str(icon_path))
        strings = {
            "idle": self._t("Ruhemodus"),
            "system_locked": self._t("System gesperrt"),
            "standby": self._t("Standby"),
            "entering_standby": self._t("Standby wird vorbereitet"),
            "shutting_down": self._t("Herunterfahren"),
            "restarting": self._t("Neustart"),
        }
        image = render_system_state_image(
            int(self.canvas.canvas_size.width),
            int(self.canvas.canvas_size.height),
            state,
            self.preferences.system_state_theme,
            icon,
            strings,
        )
        encoded = QByteArray()
        buffer = QBuffer(encoded)
        if not buffer.open(QBuffer.WriteOnly):
            return None
        if not image.save(buffer, "JPEG", 88):
            return None
        return bytes(encoded)

    def _show_system_state(self, state: SystemState) -> None:
        if not self._system_state_paused:
            self._system_state_live_was_active = self.live_timer.isActive()
            self._system_state_display_was_active = self.display_timer.isActive()
            self._system_state_page_cycle_was_active = self.page_cycle_timer.isActive()
            self._system_state_paused = True

        self.live_timer.stop()
        self.display_timer.stop()
        self.page_cycle_timer.stop()
        self._send_system_state_frame(state)

    def _send_system_state_frame(self, state: SystemState) -> None:
        streamer = self.display_streamer
        if not self.display_connected or streamer is None or not streamer.running:
            return
        try:
            payload = self._render_system_state_payload(state)
        except Exception as exc:
            self.statusBar().showMessage(
                f"Systemzustandsanzeige konnte nicht gerendert werden: {exc}", 4000
            )
            return
        if not payload:
            return
        self._last_display_payload = payload
        try:
            # Best effort only. OwnDash never takes a systemd sleep/shutdown
            # inhibitor, and this wait is intentionally short so OS lifecycle
            # operations are never meaningfully delayed by the display.
            streamer.submit_final(payload, timeout=0.25)
        except Exception:
            # System transitions must not fail because display I/O vanished.
            return

    def _restore_dashboard_after_system_state(self) -> None:
        if not self._system_state_paused:
            return

        live_was_active = self._system_state_live_was_active
        display_was_active = self._system_state_display_was_active
        page_cycle_was_active = self._system_state_page_cycle_was_active
        self._system_state_paused = False
        self._system_state_live_was_active = False
        self._system_state_display_was_active = False
        self._system_state_page_cycle_was_active = False

        if live_was_active:
            self.live_timer.start()
            self._refresh_live_data()
        if page_cycle_was_active:
            self.page_cycle_timer.start()

        streamer = self.display_streamer
        if (
            display_was_active
            and self.display_connected
            and streamer is not None
            and streamer.running
        ):
            self._last_display_payload = None
            self._update_display_cadence(force=True)
            self.display_timer.start()
            self._push_display_frame()

    def _refresh_visible_system_state(self) -> None:
        state = self._system_state_runtime.visible_state
        if state is not SystemState.ACTIVE:
            self._send_system_state_frame(state)

    def _stop_system_state_services(self) -> None:
        adapter = getattr(self, "_system_state_adapter", None)
        if adapter is not None:
            adapter.stop()
        idle = getattr(self, "_idle_state_monitor", None)
        if idle is not None:
            idle.stop()

    def _render_shutdown_frame_payload(self, reason: str = "quit") -> bytes | None:
        from .shutdown_frame import render_shutdown_image

        with app_icon_path() as icon_path:
            icon = QIcon(str(icon_path))
        image = render_shutdown_image(
            int(self.canvas.canvas_size.width), int(self.canvas.canvas_size.height),
            int(getattr(self, "_display_rotation", 270)), icon,
            status=self._t("Dashboard pausiert"),
            detail=self._t("Ausgabe umgestellt" if reason == "switch" else "OwnDash beendet"),
            farewell=self._t("Bis gleich."),

        )

        encoded = QByteArray()
        buffer = QBuffer(encoded)
        if not buffer.open(QBuffer.WriteOnly):
            return None
        if not image.save(buffer, "JPEG", 88):
            return None
        return bytes(encoded)

    def _show_shutdown_frame(self, reason: str = "quit") -> None:
        streamer = self.display_streamer
        if not self.display_connected or streamer is None or not streamer.running:
            return
        payload = self._render_shutdown_frame_payload(reason=reason)
        if payload:
            streamer.submit_final(payload, timeout=0.8)

    def _quit_from_tray(self) -> None:
        self._force_quit = True
        self._show_shutdown_frame()
        self._stop_display_stream()
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        will_hide_to_tray = (
            not self._force_quit
            and self.keep_display_running_on_close
            and QSystemTrayIcon.isSystemTrayAvailable()
        )
        if not will_hide_to_tray:
            self._show_shutdown_frame()
        super().closeEvent(event)
