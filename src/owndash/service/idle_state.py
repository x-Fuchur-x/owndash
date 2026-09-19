from __future__ import annotations

import logging
import os
import time
from typing import Callable, Protocol

from PySide6.QtCore import QObject, QTimer, Signal, Slot

log = logging.getLogger(__name__)

try:
    from PySide6.QtDBus import QDBusConnection, QDBusInterface
except (ImportError, OSError):  # pragma: no cover - depends on packaging/runtime
    QDBusConnection = None
    QDBusInterface = None


class IdleSource(Protocol):
    def start(self, callback: Callable[[], None]) -> bool: ...
    def stop(self) -> None: ...
    def snapshot(self) -> tuple[bool, float]: ...


def _unwrap_dbus_value(value):
    """Unwrap the common Qt DBus QVariant wrappers without depending on internals."""
    for name in ("variant", "value"):
        method = getattr(value, name, None)
        if callable(method):
            try:
                unwrapped = method()
            except TypeError:
                continue
            if unwrapped is not value:
                value = unwrapped
    return value


class _LogindIdleSource(QObject):
    """Signal-driven view of logind's session IdleHint properties."""

    _SERVICE = "org.freedesktop.login1"
    _MANAGER_PATH = "/org/freedesktop/login1"
    _MANAGER_IFACE = "org.freedesktop.login1.Manager"
    _SESSION_IFACE = "org.freedesktop.login1.Session"
    _PROPS_IFACE = "org.freedesktop.DBus.Properties"

    def __init__(self) -> None:
        super().__init__()
        self._bus = None
        self._session_path = ""
        self._callback: Callable[[], None] | None = None
        self._connected = False

    def start(self, callback: Callable[[], None]) -> bool:
        if QDBusConnection is None or QDBusInterface is None:
            return False
        try:
            bus = QDBusConnection.systemBus()
            if not bus.isConnected():
                return False
            session_id = os.environ.get("XDG_SESSION_ID", "").strip()
            if not session_id:
                return False
            manager = QDBusInterface(
                self._SERVICE,
                self._MANAGER_PATH,
                self._MANAGER_IFACE,
                bus,
            )
            if not manager.isValid():
                return False
            reply = manager.call("GetSession", session_id)
            if not reply.arguments():
                return False
            path = reply.arguments()[0]
            path = path.path() if hasattr(path, "path") else str(path)
            if not path:
                return False

            self._bus = bus
            self._session_path = path
            self._callback = callback
            self._connected = bool(
                bus.connect(
                    self._SERVICE,
                    path,
                    self._PROPS_IFACE,
                    "PropertiesChanged",
                    self,
                    "_on_properties_changed(QString,QVariantMap,QStringList)",
                )
            )
            if not self._connected:
                self.stop()
                return False
            return True
        except Exception:
            log.exception("Unable to subscribe to logind idle state")
            self.stop()
            return False

    def stop(self) -> None:
        if self._connected and self._bus is not None and self._session_path:
            try:
                self._bus.disconnect(
                    self._SERVICE,
                    self._session_path,
                    self._PROPS_IFACE,
                    "PropertiesChanged",
                    self,
                    "_on_properties_changed(QString,QVariantMap,QStringList)",
                )
            except Exception:
                pass
        self._connected = False
        self._callback = None
        self._session_path = ""
        self._bus = None

    def _read_property(self, name: str):
        if self._bus is None or QDBusInterface is None or not self._session_path:
            raise RuntimeError("logind idle source is not connected")
        props = QDBusInterface(
            self._SERVICE,
            self._session_path,
            self._PROPS_IFACE,
            self._bus,
        )
        if not props.isValid():
            raise RuntimeError("logind session properties are unavailable")
        reply = props.call("Get", self._SESSION_IFACE, name)
        if not reply.arguments():
            raise RuntimeError(f"logind property {name} is unavailable")
        return _unwrap_dbus_value(reply.arguments()[0])

    def snapshot(self) -> tuple[bool, float]:
        idle = bool(self._read_property("IdleHint"))
        if not idle:
            return False, 0.0
        # logind exposes IdleSinceHintMonotonic in microseconds on CLOCK_MONOTONIC.
        usec = int(self._read_property("IdleSinceHintMonotonic") or 0)
        return True, max(0.0, usec / 1_000_000.0)

    @Slot(str, "QVariantMap", "QStringList")
    def _on_properties_changed(self, interface: str, changed: dict, invalidated: list) -> None:
        if interface != self._SESSION_IFACE:
            return
        watched = {"IdleHint", "IdleSinceHintMonotonic"}
        if watched.intersection(changed) or watched.intersection(invalidated):
            callback = self._callback
            if callback is not None:
                callback()


class IdleStateMonitor(QObject):
    """Convert logind's session idle hint into a configurable OwnDash idle state.

    The monitor is event-driven while the session is active. If logind reports
    that the session is idle but the user-configured delay has not elapsed yet,
    one single-shot timer is scheduled for the remaining delay. No periodic
    polling is used in the common active state.
    """

    idle_changed = Signal(bool)
    # The service layer accepts short values for deterministic tests and future
    # integrations. The user-facing preference is stricter (minutes, >= 1).
    MIN_IDLE_SECONDS = 5
    MAX_IDLE_SECONDS = 24 * 60 * 60

    def __init__(
        self,
        *,
        source: IdleSource | None = None,
        timeout_seconds: int | float = 30 * 60,
        clock: Callable[[], float] = time.monotonic,
        enabled: bool = True,
        auto_schedule: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._source: IdleSource = source or _LogindIdleSource()
        self._clock = clock
        self._enabled = bool(enabled)
        self._available = False
        self._idle = False
        self._timeout_seconds = self._clamp_timeout(timeout_seconds)
        self._auto_schedule = bool(auto_schedule)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.check)

    @classmethod
    def _clamp_timeout(cls, value: int | float) -> int:
        try:
            seconds = int(value)
        except (TypeError, ValueError, OverflowError):
            seconds = cls.MIN_IDLE_SECONDS
        return max(cls.MIN_IDLE_SECONDS, min(cls.MAX_IDLE_SECONDS, seconds))

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def is_idle(self) -> bool:
        return self._idle

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._enabled:
            return
        self._enabled = enabled
        if not enabled:
            self._timer.stop()
            self._set_idle(False)
        elif self._available:
            self.check()

    def set_timeout_seconds(self, value: int | float) -> None:
        timeout = self._clamp_timeout(value)
        if timeout == self._timeout_seconds:
            return
        self._timeout_seconds = timeout
        if self._available and self._enabled:
            self.check()

    def start(self) -> bool:
        if self._available:
            return True
        try:
            self._available = bool(self._source.start(self._source_changed))
        except Exception:
            log.exception("Idle-state source failed to start")
            self._available = False
        if self._available:
            self.check()
        return self._available

    def stop(self) -> None:
        self._timer.stop()
        try:
            self._source.stop()
        except Exception:
            log.debug("Idle-state source failed to stop cleanly", exc_info=True)
        self._available = False
        # Stopping infrastructure during app teardown is not a user-visible
        # activity transition, so reset silently.
        self._idle = False

    def _source_changed(self) -> None:
        self.check()

    def check(self) -> None:
        self._timer.stop()
        if not self._available or not self._enabled:
            self._set_idle(False)
            return
        try:
            hinted_idle, idle_since = self._source.snapshot()
        except Exception:
            log.debug("Unable to read logind idle state", exc_info=True)
            self._set_idle(False)
            return

        if not hinted_idle:
            self._set_idle(False)
            return

        elapsed = max(0.0, float(self._clock()) - max(0.0, float(idle_since)))
        remaining = self._timeout_seconds - elapsed
        if remaining <= 0:
            self._set_idle(True)
            return

        self._set_idle(False)
        if self._auto_schedule:
            # One wake-up exactly when the configured OwnDash delay expires;
            # clamp to Qt's signed-int millisecond range for safety.
            delay_ms = max(1, min(2_147_483_647, int(remaining * 1000 + 0.999)))
            self._timer.start(delay_ms)

    def _set_idle(self, idle: bool) -> None:
        idle = bool(idle)
        if idle == self._idle:
            return
        self._idle = idle
        self.idle_changed.emit(idle)
