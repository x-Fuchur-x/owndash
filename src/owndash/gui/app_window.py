from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from owndash import APP_NAME
from owndash.assets import app_icon_path

from .main_window import MainWindow


class SafeShutdownWindow(MainWindow):
    """Main window lifecycle that leaves displays in a defined branded state."""

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
