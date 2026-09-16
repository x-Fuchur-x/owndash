from __future__ import annotations

from threading import Thread
import webbrowser

from PySide6.QtCore import QBuffer, QByteArray, QObject, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QLinearGradient, QPainter, QPen
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
from owndash.core.updates import ReleaseInfo, fetch_available_update
from owndash.i18n import resolved_language

from .main_window import MainWindow


class UpdateBridge(QObject):
    """Marshal background update results safely back onto the Qt GUI thread."""

    completed = Signal(object)


class SafeShutdownWindow(MainWindow):
    """OwnDash lifecycle extensions for safe shutdown and update awareness."""

    def __init__(self):
        super().__init__()
        self._update_bridge = UpdateBridge(self)
        self._update_bridge.completed.connect(self._handle_update_result)
        self._update_check_started = False
        self._update_dialog: QMessageBox | None = None
        self._schedule_update_check()

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
        """Show general settings, including the optional background update check."""
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
        save_preferences(self.preferences)

        self.language = resolved_language(self.preferences.language)
        apply_appearance(self.preferences.appearance, self._system_palette)
        self._apply_ui_polish()
        self._retranslate_ui()
        self.statusBar().showMessage(self._t("Bereit · Live-Vorschau aktiv"), 2500)

        if self.preferences.check_updates and not was_checking_updates:
            self._schedule_update_check()

    def _render_shutdown_frame_payload(self) -> bytes | None:
        width = max(320, int(self.canvas.canvas_size.width))
        height = max(120, int(self.canvas.canvas_size.height))
        image = QImage(width, height, QImage.Format_RGB32)

        background = QLinearGradient(0, 0, width, height)
        background.setColorAt(0.0, QColor("#06111b"))
        background.setColorAt(1.0, QColor("#0a1020"))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(0, 0, width, height, background)

        card_w = min(width - 40, max(240, int(width * 0.72)))
        card_h = min(height - 32, max(96, int(height * 0.58)))
        card_x = (width - card_w) // 2
        card_y = (height - card_h) // 2

        painter.setPen(QPen(QColor("#3b82f6"), 2))
        painter.setBrush(QColor(8, 15, 26, 232))
        painter.drawRoundedRect(card_x, card_y, card_w, card_h, 24, 24)

        icon_size = max(48, min(96, card_h - 34))
        with app_icon_path() as icon_path:
            icon = QIcon(str(icon_path))
        painter.drawPixmap(
            card_x + 22,
            card_y + (card_h - icon_size) // 2,
            icon.pixmap(icon_size, icon_size),
        )

        text_x = card_x + 22 + icon_size + 20
        text_w = max(120, card_x + card_w - text_x - 20)

        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(max(12, min(28, height // 18)))
        painter.setFont(title_font)
        painter.setPen(QColor("#f8fafc"))
        painter.drawText(
            text_x,
            card_y + 12,
            text_w,
            max(36, card_h // 3),
            Qt.AlignLeft | Qt.AlignVCenter,
            APP_NAME,
        )

        subtitle_font = QFont()
        subtitle_font.setPointSize(max(9, min(18, height // 30)))
        painter.setFont(subtitle_font)
        painter.setPen(QColor("#9fb6ff"))
        painter.drawText(
            text_x,
            card_y + card_h // 3,
            text_w,
            max(28, card_h // 4),
            Qt.AlignLeft | Qt.AlignVCenter,
            "Shutting down…",
        )

        painter.setPen(QColor("#6b7a96"))
        painter.drawText(
            card_x + 22,
            card_y + card_h - 34,
            card_w - 44,
            22,
            Qt.AlignLeft | Qt.AlignVCenter,
            "Your display. Your design.",
        )
        painter.end()

        encoded = QByteArray()
        buffer = QBuffer(encoded)
        if not buffer.open(QBuffer.WriteOnly):
            return None
        if not image.save(buffer, "JPEG", 88):
            return None
        return bytes(encoded)

    def _show_shutdown_frame(self) -> None:
        streamer = self.display_streamer
        if not self.display_connected or streamer is None or not streamer.running:
            return
        payload = self._render_shutdown_frame_payload()
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
