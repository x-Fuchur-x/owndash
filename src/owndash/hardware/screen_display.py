from __future__ import annotations

from dataclasses import dataclass
import io

from PIL import Image
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from owndash.core.display import DisplayBackend, DisplayInfo, DisplayProtocolError


class FullscreenDisplayWindow(QWidget):
    escape_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Escape, Qt.Key_F11):
            self.escape_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ScreenPresenter(QObject):
    frame_ready = Signal(bytes)
    close_requested = Signal()

    def __init__(self, geometry, parent: QObject | None = None, *, screen=None):  # noqa: ANN001
        super().__init__(parent)
        self.geometry = geometry
        self.screen = screen
        self.window = FullscreenDisplayWindow()
        self.window.setWindowTitle("OwnDash Display")
        self.window.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.window.setFocusPolicy(Qt.StrongFocus)
        self.window.escape_requested.connect(self.close_requested.emit)
        self.label = QLabel(self.window)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background: black;")
        self.frame_ready.connect(self._show_frame)
        self.close_requested.connect(self._close)

    def open(self) -> None:
        # Position alone is not a screen selection on Wayland. Set the native
        # window's target before requesting fullscreen; retain geometry for X11.
        if self.screen is not None:
            self.window.winId()
            self.window.windowHandle().setScreen(self.screen)
        self.window.setGeometry(self.geometry)
        self.label.setGeometry(self.window.rect())
        self.window.showFullScreen()
        self.window.raise_()
        self.window.activateWindow()
        self.window.setFocus(Qt.ActiveWindowFocusReason)

    def _show_frame(self, payload: bytes) -> None:
        if not self.window.isVisible():
            self.open()
        self.label.setGeometry(self.window.rect())
        pixmap = QPixmap()
        if not pixmap.loadFromData(payload, "JPEG"):
            return
        ratio = self.window.devicePixelRatioF()
        fitted = pixmap.scaled(self.label.size() * ratio, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        fitted.setDevicePixelRatio(ratio)
        self.label.setPixmap(fitted)

    def _close(self) -> None:
        self.window.hide()


@dataclass(slots=True)
class ScreenBackendSettings:
    name: str
    width: int
    height: int
    geometry: object
    rotation: int = 0


class ScreenDisplayBackend(DisplayBackend):
    """Output backend for ordinary Linux monitors/HDMI/DP/USB-C displays.

    Rendering stays in OwnDash; JPEG frames are queued back to a presenter that
    lives on Qt's GUI thread.
    """

    def __init__(self, presenter: ScreenPresenter, settings: ScreenBackendSettings):
        self.presenter = presenter
        self.settings = settings
        self._connected = False

    def connect(self) -> DisplayInfo:
        self._connected = True
        return DisplayInfo(
            self.settings.name,
            self.settings.width,
            self.settings.height,
            None,
        )

    def send_jpeg(self, payload: bytes) -> None:
        if not self._connected:
            raise DisplayProtocolError("Display ist nicht verbunden.")
        rotation = int(self.settings.rotation) % 360
        frame = bytes(payload)
        if rotation:
            if rotation not in {90, 180, 270}:
                raise DisplayProtocolError("Rotation muss 0, 90, 180 oder 270 Grad sein.")
            try:
                with Image.open(io.BytesIO(frame)) as source:
                    image = source.convert("RGB").rotate(-rotation, expand=True)
                    output = io.BytesIO()
                    image.save(output, format="JPEG", quality=82)
                    frame = output.getvalue()
            except OSError as exc:
                raise DisplayProtocolError("Ungültiger JPEG-Frame.") from exc
        self.presenter.frame_ready.emit(frame)

    def close(self) -> None:
        self._connected = False
        self.presenter.close_requested.emit()
