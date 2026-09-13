from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


ACTIVATE_MESSAGE = b"activate\n"


def notify_existing_instance(server_name: str, *, timeout_ms: int = 250) -> bool:
    """Ask an already-running OwnDash instance to show itself."""
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if not socket.waitForConnected(timeout_ms):
        socket.abort()
        return False

    socket.write(ACTIVATE_MESSAGE)
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


class SingleInstanceServer(QObject):
    """Owns the per-user local IPC endpoint for the primary OwnDash process."""

    activation_requested = Signal()

    def __init__(self, server_name: str, parent: QObject | None = None):
        super().__init__(parent)
        self.server_name = server_name
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._handle_connections)
        self._pending_activation = False

    def listen(self) -> bool:
        if self.server.listen(self.server_name):
            return True

        # A crashed process may leave behind a stale Unix-domain socket.
        # Only remove it after we have already failed to contact a live instance.
        QLocalServer.removeServer(self.server_name)
        return self.server.listen(self.server_name)

    def _handle_connections(self) -> None:
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if socket is None:
                continue
            if not socket.waitForReadyRead(100):
                socket.disconnectFromServer()
                socket.deleteLater()
                continue
            payload = bytes(socket.readAll())
            if ACTIVATE_MESSAGE.strip() in payload:
                self._pending_activation = True
                self.activation_requested.emit()
            socket.disconnectFromServer()
            socket.deleteLater()

    def consume_pending_activation(self) -> bool:
        pending = self._pending_activation
        self._pending_activation = False
        return pending
