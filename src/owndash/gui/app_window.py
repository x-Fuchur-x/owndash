from __future__ import annotations

from datetime import datetime
from threading import Thread
import webbrowser

from PySide6.QtCore import QBuffer, QByteArray, QObject, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QImage, QLinearGradient, QPainter, QPen, QTransform
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
from owndash.hardware.usb_setup import (
    install_udev_rule,
    legacy_udev_rule_installed,
    probe_artinchip_usb,
)
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

    _RESUME_RECONNECT_DELAYS_MS = (600, 800, 1000, 1200, 1400)
    _SYSTEM_STATE_ANIMATION_INTERVAL_MS = 750

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

        # System-state screens are event-driven. Normal sensor/display/page
        # timers stop while a state screen is visible. Only IDLE/LOCKED get a
        # deliberately slow HUD timer; terminal/suspend states remain a single
        # static frame that is safe to freeze while the PC sleeps.
        self._system_state_paused = False
        self._system_state_live_was_active = False
        self._system_state_display_was_active = False
        self._system_state_page_cycle_was_active = False
        self._resume_reconnect_pending = False
        self._resume_recovery_armed = False
        self._resume_reconnect_attempt = 0
        self._system_state_animation_phase = 0.0
        self._system_state_animation_timer = QTimer(self)
        self._system_state_animation_timer.setInterval(
            self._SYSTEM_STATE_ANIMATION_INTERVAL_MS
        )
        self._system_state_animation_timer.timeout.connect(
            self._advance_system_state_animation
        )
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
        self._resume_reconnect_pending = False
        self._resume_recovery_armed = False
        self._resume_reconnect_attempt = 0
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
            self._configure_system_state_animation(runtime.visible_state)

    def _push_display_frame(self) -> None:
        runtime = getattr(self, "_system_state_runtime", None)
        if runtime is not None and runtime.visible_state is not SystemState.ACTIVE:
            return
        super()._push_display_frame()

    def _prepare_display_switch(self) -> None:
        if self.display_backend_key == "aic_usb":
            self.display_timer.stop()
            self._show_shutdown_frame(reason="switch")

    def _start_display_stream(self) -> None:
        """Start output only after migrating the obsolete late uaccess rule.

        The old 99-* rule can appear to work until suspend causes the USB device
        to enumerate again. Requiring the existing one-click setup before a USB
        stream starts prevents that known-bad configuration from surviving into
        the next resume cycle.
        """
        if self.display_backend_key == "aic_usb" and legacy_udev_rule_installed():
            answer = QMessageBox.question(
                self,
                self._t("USB-Zugriff"),
                self._t("Das USB-Display wurde erkannt, OwnDash benötigt aber noch Zugriffsrechte."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.display_action.blockSignals(True)
                self.display_action.setChecked(False)
                self.display_action.blockSignals(False)
                return
            ok, message = install_udev_rule()
            if not ok:
                QMessageBox.warning(self, self._t("USB-Zugriff"), self._t(message))
                self.display_action.blockSignals(True)
                self.display_action.setChecked(False)
                self.display_action.blockSignals(False)
                return
            self.statusBar().showMessage(self._t(message), 4000)
        super()._start_display_stream()

    def _stop_display_stream(self) -> None:
        self._resume_reconnect_pending = False
        self._resume_recovery_armed = False
        self._resume_reconnect_attempt = 0
        self._system_state_animation_timer.stop()
        self._connected_display_info = None
        if hasattr(self, "display_controls_action"):
            self.display_controls_action.setEnabled(False)
        super()._stop_display_stream()

    def _display_error(self, error: object) -> None:
        runtime = getattr(self, "_system_state_runtime", None)
        current_state = runtime.visible_state if runtime is not None else SystemState.ACTIVE
        recoverable_resume_error = (
            self.display_backend_key == "aic_usb"
            and (
                current_state is SystemState.SUSPENDING
                or self._resume_recovery_armed
                or self._resume_reconnect_pending
            )
        )
        if recoverable_resume_error:
            was_pending = self._resume_reconnect_pending
            self._resume_reconnect_pending = True
            self._resume_recovery_armed = True
            if not was_pending:
                self._resume_reconnect_attempt = 0
            self._quiet_reset_display_after_error()
            if current_state is not SystemState.SUSPENDING:
                self.statusBar().showMessage(
                    self._t("Display wird nach Standby neu verbunden …"), 3000
                )
                self._queue_usb_resume_reconnect()
            return

        self._connected_display_info = None
        if hasattr(self, "display_controls_action"):
            self.display_controls_action.setEnabled(False)
        super()._display_error(error)

    def _quiet_reset_display_after_error(self) -> None:
        """Release a failed USB stream without showing a suspend-time dialog."""
        self.display_timer.stop()
        self.display_connected = False
        self._connected_display_info = None
        if hasattr(self, "display_controls_action"):
            self.display_controls_action.setEnabled(False)

        streamer = self.display_streamer
        self.display_streamer = None
        if streamer is not None:
            try:
                streamer.stop(timeout=0.2)
            except Exception:
                pass

        self.display_action.blockSignals(True)
        self.display_action.setChecked(False)
        self.display_action.setText(self._t("Display starten"))
        self.display_action.setEnabled(True)
        self.display_action.blockSignals(False)
        if hasattr(self, "tray_display_action"):
            self.tray_display_action.setEnabled(False)
            self.tray_display_action.setText(self._t("Display ist gestoppt"))

    def _schedule_usb_resume_reconnect(self) -> None:
        """Start a short, bounded post-resume recovery window.

        USB displays often enumerate in stages after system resume: absent,
        present without the logind ACL, then accessible. Probing these states
        before opening PyUSB prevents transient conditions from surfacing as
        user-facing errors. This timer chain exists only after resume and stops
        immediately on success or after roughly five seconds.
        """
        if self.display_backend_key != "aic_usb":
            self._resume_reconnect_pending = False
            self._resume_recovery_armed = False
            self._resume_reconnect_attempt = 0
            return
        self._resume_reconnect_pending = True
        self._resume_recovery_armed = True
        self._resume_reconnect_attempt = 0
        self.statusBar().showMessage(
            self._t("Display wird nach Standby neu verbunden …"), 3000
        )
        self._queue_usb_resume_reconnect()

    def _queue_usb_resume_reconnect(self) -> None:
        if not self._resume_reconnect_pending or self.display_backend_key != "aic_usb":
            return
        if self._resume_reconnect_attempt >= len(self._RESUME_RECONNECT_DELAYS_MS):
            self._finish_usb_resume_recovery_failure()
            return
        delay = self._RESUME_RECONNECT_DELAYS_MS[self._resume_reconnect_attempt]
        self._resume_reconnect_attempt += 1
        QTimer.singleShot(int(delay), self._attempt_usb_resume_reconnect)

    def _attempt_usb_resume_reconnect(self) -> None:
        if not self._resume_reconnect_pending or self.display_backend_key != "aic_usb":
            return
        status = probe_artinchip_usb()
        if status.connected and status.accessible:
            # Keep the recovery flags armed until _display_connected arrives.
            # If the backend still fails while opening the device, _display_error
            # quietly advances to the next bounded retry instead of showing a
            # transient dialog.
            self._start_display_stream()
            return
        self._queue_usb_resume_reconnect()

    def _finish_usb_resume_recovery_failure(self) -> None:
        if not self._resume_reconnect_pending:
            return
        status = probe_artinchip_usb()
        self._resume_reconnect_pending = False
        self._resume_recovery_armed = False
        self._resume_reconnect_attempt = 0
        if status.connected:
            message = self._t(
                "Das USB-Display wurde erkannt, OwnDash benötigt aber noch Zugriffsrechte."
            )
        else:
            message = self._t("Display nicht verbunden")
        # Resume must stay unobtrusive. A failed bounded recovery leaves the
        # display stopped and reports the state in the main window instead of
        # throwing a modal dialog over the freshly unlocked desktop.
        self.statusBar().showMessage(message, 8000)

    def _clear_resume_recovery_arm(self) -> None:
        if not self._resume_reconnect_pending:
            self._resume_recovery_armed = False

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
            self._resume_reconnect_pending = False
            self._resume_recovery_armed = False
            self._resume_reconnect_attempt = 0
            self._system_state_animation_timer.stop()
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

        is_suspend_start = state is SystemState.SUSPENDING and bool(enabled)
        is_resume = state is SystemState.SUSPENDING and not bool(enabled)
        if is_suspend_start:
            self._resume_reconnect_pending = False
            self._resume_recovery_armed = False
            self._resume_reconnect_attempt = 0
        elif is_resume and self.display_backend_key == "aic_usb":
            if self._system_state_display_was_active or self._resume_reconnect_pending:
                self._resume_recovery_armed = True
                if not self._resume_reconnect_pending:
                    # The display may survive suspend and only fail when its
                    # first post-resume transfer occurs. Keep that transient
                    # failure quiet for a bounded window, not indefinitely.
                    QTimer.singleShot(12000, self._clear_resume_recovery_arm)

        self._system_state_runtime.handle_condition(state, bool(enabled))

        if is_resume and self._resume_reconnect_pending:
            self._schedule_usb_resume_reconnect()

    def _render_system_state_payload(
        self,
        state: SystemState,
        *,
        animation_phase: float = 0.0,
    ) -> bytes | None:
        if state is SystemState.ACTIVE:
            return None
        with app_icon_path() as icon_path:
            icon = QIcon(str(icon_path))
        strings = {
            "idle": self._t("Ruhemodus"),
            "system_locked": self._t("System gesperrt"),
            "standby": self._t("Standby"),
            "entering_standby": self._t("Standby wird vorbereitet"),
            "system_transition": self._t("Systemwechsel"),
            "ending_session": self._t("OwnDash beendet die aktuelle Sitzung."),
            "shutting_down": self._t("Herunterfahren"),
            "restarting": self._t("Neustart"),
        }
        now = datetime.now()
        clock_text = now.strftime("%H:%M") if state in {SystemState.IDLE, SystemState.LOCKED} else None
        if self.language == "de":
            date_text = now.strftime("%d.%m.%Y")
        else:
            date_text = now.strftime("%Y-%m-%d")

        logical_w = int(self.canvas.canvas_size.width)
        logical_h = int(self.canvas.canvas_size.height)
        rotation = int(getattr(self, "_display_rotation", 0)) % 360
        rotate_for_transport = self.display_backend_key == "aic_usb" and rotation in {90, 270}
        render_w, render_h = (logical_h, logical_w) if rotate_for_transport else (logical_w, logical_h)

        image = render_system_state_image(
            render_w,
            render_h,
            state,
            self.preferences.system_state_theme,
            icon,
            strings,
            clock_text=clock_text,
            date_text=date_text if state is SystemState.LOCKED else None,
            animation_phase=animation_phase,
        )
        if rotate_for_transport:
            # The USB backend rotates the JPEG into panel orientation. Build the
            # state art in the physical portrait orientation first, then apply
            # the inverse transport rotation so the backend lands on that exact
            # composition instead of rotating a landscape layout into portrait.
            pre_angle = 90 if rotation == 270 else -90
            image = image.transformed(QTransform().rotate(pre_angle), Qt.SmoothTransformation)

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
        self._system_state_animation_timer.stop()
        self._system_state_animation_phase = 0.0
        self._send_system_state_frame(state)
        self._configure_system_state_animation(state)

    def _configure_system_state_animation(self, state: SystemState) -> None:
        if (
            state in {SystemState.IDLE, SystemState.LOCKED}
            and self.display_connected
            and self.display_streamer is not None
            and self.display_streamer.running
        ):
            if not self._system_state_animation_timer.isActive():
                self._system_state_animation_timer.start()
        else:
            self._system_state_animation_timer.stop()

    def _advance_system_state_animation(self) -> None:
        state = self._system_state_runtime.visible_state
        if state not in {SystemState.IDLE, SystemState.LOCKED}:
            self._system_state_animation_timer.stop()
            return
        if not self.display_connected or self.display_streamer is None or not self.display_streamer.running:
            self._system_state_animation_timer.stop()
            return
        self._system_state_animation_phase = (self._system_state_animation_phase + 0.125) % 1.0
        self._send_system_state_frame(
            state,
            final=False,
            animation_phase=self._system_state_animation_phase,
        )

    def _send_system_state_frame(
        self,
        state: SystemState,
        *,
        final: bool = True,
        animation_phase: float | None = None,
    ) -> None:
        streamer = self.display_streamer
        if not self.display_connected or streamer is None or not streamer.running:
            return
        try:
            phase = self._system_state_animation_phase if animation_phase is None else animation_phase
            payload = self._render_system_state_payload(state, animation_phase=phase)
        except Exception as exc:
            self.statusBar().showMessage(
                f"{self._t('Systemzustandsanzeige konnte nicht gerendert werden')}: {exc}",
                4000,
            )
            return
        if not payload:
            return
        self._last_display_payload = payload
        try:
            if final:
                # Best effort only. OwnDash never takes a systemd sleep/shutdown
                # inhibitor, and this wait is intentionally short so OS lifecycle
                # operations are never meaningfully delayed by the display.
                streamer.submit_final(payload, timeout=0.25)
            else:
                # Slow lock/idle HUD frames use the streamer's normal coalescing
                # queue and never block the UI thread waiting for USB transfer.
                streamer.submit(payload)
        except Exception:
            # System transitions must not fail because display I/O vanished.
            return

    def _restore_dashboard_after_system_state(self) -> None:
        if not self._system_state_paused:
            return

        self._system_state_animation_timer.stop()
        self._system_state_animation_phase = 0.0
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
            self._system_state_animation_phase = 0.0
            self._send_system_state_frame(state)
            self._configure_system_state_animation(state)

    def _stop_system_state_services(self) -> None:
        self._system_state_animation_timer.stop()
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
