from __future__ import annotations

import logging
import os
from typing import Callable, Protocol

from PySide6.QtCore import QObject, Signal, Slot, SLOT

from owndash.core.system_state import SystemState

log = logging.getLogger(__name__)

try:  # QtDBus is optional at runtime (not all PySide/AppImage builds include it).
    from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusObjectPath
except (ImportError, OSError):  # pragma: no cover - exercised through injected unavailable sources
    QDBusConnection = None
    QDBusInterface = None
    # Keep the module importable when QtDBus is unavailable. The fallback type
    # is never used for a live connection in that case.
    QDBusObjectPath = object


SourceCallback = Callable[[str, bool], None]


class SystemStateSource(Protocol):
    def start(self, callback: SourceCallback) -> bool: ...
    def stop(self) -> None: ...


class _LogindDbusSource(QObject):
    """Best-effort, low-overhead systemd-logind signal source.

    It subscribes to event signals; there is no polling loop. Restart is only
    reported when there is positive evidence (a scheduled reboot or a systemd
    reboot target job). Ambiguous PrepareForShutdown events stay neutral until
    systemd exposes whether the machine is rebooting or powering off.
    """

    _LOGIN_SERVICE = "org.freedesktop.login1"
    _LOGIN_PATH = "/org/freedesktop/login1"
    _LOGIN_MANAGER = "org.freedesktop.login1.Manager"
    _LOGIN_SESSION = "org.freedesktop.login1.Session"
    _SYSTEMD_SERVICE = "org.freedesktop.systemd1"
    _SYSTEMD_PATH = "/org/freedesktop/systemd1"
    _SYSTEMD_MANAGER = "org.freedesktop.systemd1.Manager"

    def __init__(self) -> None:
        super().__init__()
        self._callback: SourceCallback | None = None
        self._bus = None
        self._session_path = ""
        self._terminal_kind = "terminal_pending"
        self._terminal_active = False
        self._pending_terminal_kind: str | None = None
        self._connections: list[tuple[str, str, str, str, str]] = []

    def start(self, callback: SourceCallback) -> bool:
        if QDBusConnection is None or QDBusInterface is None:
            return False
        try:
            bus = QDBusConnection.systemBus()
            if not bus.isConnected():
                return False
            interface = bus.interface()
            if interface is None:
                return False
            registered = interface.isServiceRegistered(self._LOGIN_SERVICE)
            value = registered.value() if hasattr(registered, "value") else bool(registered)
            if not value:
                return False

            self._bus = bus
            self._callback = callback
            ok = True
            ok &= self._connect(
                self._LOGIN_SERVICE, self._LOGIN_PATH, self._LOGIN_MANAGER,
                "PrepareForSleep", "_on_prepare_for_sleep(bool)",
            )
            ok &= self._connect(
                self._LOGIN_SERVICE, self._LOGIN_PATH, self._LOGIN_MANAGER,
                "PrepareForShutdown", "_on_prepare_for_shutdown(bool)",
            )
            # systemd JobNew gives positive evidence for immediate reboot versus power-off.
            self._connect(
                self._SYSTEMD_SERVICE, self._SYSTEMD_PATH, self._SYSTEMD_MANAGER,
                "JobNew", "_on_job_new(uint,QDBusObjectPath,QString)",
            )
            self._session_path = self._get_session_path()
            if self._session_path:
                # Lock/Unlock are useful best-effort request signals. LockedHint
                # is the authoritative session state, so also subscribe to its
                # PropertiesChanged updates without introducing a polling loop.
                self._connect(
                    self._LOGIN_SERVICE, self._session_path,
                    self._LOGIN_SESSION, "Lock", "_on_lock()",
                )
                self._connect(
                    self._LOGIN_SERVICE, self._session_path,
                    self._LOGIN_SESSION, "Unlock", "_on_unlock()",
                )
                self._connect(
                    self._LOGIN_SERVICE, self._session_path,
                    "org.freedesktop.DBus.Properties", "PropertiesChanged",
                    "_on_session_properties_changed(QString,QVariantMap,QStringList)",
                )
                # Read LockedHint exactly once so an already locked desktop is
                # represented immediately at app startup. Future changes arrive
                # through PropertiesChanged, so no polling is required.
                locked = self._session_locked_hint()
                if locked is not None:
                    self._emit("lock", locked)
            if not ok:
                self.stop()
                return False
            return True
        except Exception:
            log.exception("Unable to subscribe to systemd-logind system-state signals")
            self.stop()
            return False

    def stop(self) -> None:
        bus = self._bus
        if bus is not None:
            for service, path, interface, name, slot in self._connections:
                try:
                    bus.disconnect(service, path, interface, name, self, slot)
                except Exception:
                    pass
        self._connections.clear()
        self._callback = None
        self._bus = None
        self._session_path = ""
        self._pending_terminal_kind = None
        self._terminal_active = False
        self._terminal_kind = "terminal_pending"

    def _connect(self, service: str, path: str, interface: str, name: str, slot: str) -> bool:
        assert self._bus is not None
        # PySide's QtDBus binding still expects the old Qt SLOT()-encoded
        # string here. Passing the bare meta-object signature looks plausible
        # and works with simple fakes, but real QDBusConnection rejects it.
        qt_slot = SLOT(slot)
        connected = bool(self._bus.connect(service, path, interface, name, self, qt_slot))
        if connected:
            self._connections.append((service, path, interface, name, qt_slot))
        return connected

    def _get_session_path(self) -> str:
        session_id = os.environ.get("XDG_SESSION_ID", "").strip()
        if not session_id or self._bus is None or QDBusInterface is None:
            return ""
        manager = QDBusInterface(
            self._LOGIN_SERVICE, self._LOGIN_PATH, self._LOGIN_MANAGER, self._bus
        )
        if not manager.isValid():
            return ""
        reply = manager.call("GetSession", session_id)
        if reply.type() == reply.MessageType.ErrorMessage or not reply.arguments():
            return ""
        path = reply.arguments()[0]
        return path.path() if hasattr(path, "path") else str(path)

    def _session_locked_hint(self) -> bool | None:
        if not self._session_path or self._bus is None or QDBusInterface is None:
            return None
        props = QDBusInterface(
            self._LOGIN_SERVICE,
            self._session_path,
            "org.freedesktop.DBus.Properties",
            self._bus,
        )
        if not props.isValid():
            return None
        try:
            reply = props.call("Get", self._LOGIN_SESSION, "LockedHint")
            if not reply.arguments():
                return None
            value = reply.arguments()[0]
            value = value.variant() if hasattr(value, "variant") else value
            return value if isinstance(value, bool) else None
        except Exception:
            log.debug("Could not inspect session LockedHint", exc_info=True)
            return None

    def _scheduled_shutdown_kind(self) -> str | None:
        if self._bus is None or QDBusInterface is None:
            return None
        props = QDBusInterface(
            self._LOGIN_SERVICE,
            self._LOGIN_PATH,
            "org.freedesktop.DBus.Properties",
            self._bus,
        )
        if not props.isValid():
            return None
        try:
            reply = props.call("Get", self._LOGIN_MANAGER, "ScheduledShutdown")
            if not reply.arguments():
                return None
            value = reply.arguments()[0]
            value = value.variant() if hasattr(value, "variant") else value
            if isinstance(value, (tuple, list)) and value:
                kind = str(value[0]).lower()
                return "restart" if kind in {"reboot", "kexec"} else "shutdown"
        except Exception:
            log.debug("Could not inspect logind ScheduledShutdown", exc_info=True)
        return None

    def _emit(self, kind: str, enabled: bool) -> None:
        callback = self._callback
        if callback is not None:
            callback(kind, enabled)

    @Slot(bool)
    def _on_prepare_for_sleep(self, start: bool) -> None:
        self._emit("sleep", bool(start))

    @Slot()
    def _on_lock(self) -> None:
        self._emit("lock", True)

    @Slot()
    def _on_unlock(self) -> None:
        self._emit("lock", False)

    @Slot(str, "QVariantMap", "QStringList")
    def _on_session_properties_changed(
        self,
        interface: str,
        changed: dict,
        invalidated: list[str],
    ) -> None:
        if str(interface) != self._LOGIN_SESSION:
            return
        if "LockedHint" in changed:
            value = changed["LockedHint"]
            value = value.variant() if hasattr(value, "variant") else value
            if isinstance(value, bool):
                self._emit("lock", value)
            return
        if "LockedHint" in invalidated:
            locked = self._session_locked_hint()
            if locked is not None:
                self._emit("lock", locked)

    @Slot("uint", QDBusObjectPath, str)
    def _on_job_new(self, _job_id: int, _job_path: object, unit: str) -> None:
        unit = str(unit)
        new_kind: str | None = None
        if unit in {"reboot.target", "soft-reboot.target", "kexec.target"}:
            new_kind = "restart"
        elif unit in {"poweroff.target", "halt.target"}:
            new_kind = "shutdown"
        if new_kind is None:
            return

        self._pending_terminal_kind = new_kind
        if self._terminal_active and self._terminal_kind == "terminal_pending":
            self._emit("terminal_pending", False)
            self._terminal_kind = new_kind
            self._pending_terminal_kind = None
            self._emit(new_kind, True)

    @Slot(bool)
    def _on_prepare_for_shutdown(self, start: bool) -> None:
        if start:
            self._terminal_active = True
            self._terminal_kind = (
                self._pending_terminal_kind
                or self._scheduled_shutdown_kind()
                or "terminal_pending"
            )
            self._pending_terminal_kind = None
            self._emit(self._terminal_kind, True)
            return

        self._emit(self._terminal_kind, False)
        self._terminal_active = False
        self._terminal_kind = "terminal_pending"
        self._pending_terminal_kind = None


class LinuxSystemStateAdapter(QObject):
    """Translate Linux source events into normalized OwnDash conditions."""

    condition_changed = Signal(object, bool)
    availability_changed = Signal(bool)

    _EVENT_TO_STATE = {
        "sleep": SystemState.SUSPENDING,
        "lock": SystemState.LOCKED,
        "terminal_pending": SystemState.TRANSITIONING,
        "shutdown": SystemState.SHUTTING_DOWN,
        "restart": SystemState.RESTARTING,
    }

    def __init__(self, source: SystemStateSource | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: SystemStateSource = source or _LogindDbusSource()
        self._available = False
        self._conditions: dict[SystemState, bool] = {}

    @property
    def is_available(self) -> bool:
        return self._available

    def start(self) -> bool:
        if self._available:
            return True
        try:
            available = bool(self._source.start(self._on_source_event))
        except Exception:
            log.exception("System-state source failed to start")
            available = False
        self._set_available(available)
        return available

    def stop(self) -> None:
        try:
            self._source.stop()
        except Exception:
            log.debug("System-state source failed to stop cleanly", exc_info=True)
        self._conditions.clear()
        self._set_available(False)

    def _set_available(self, available: bool) -> None:
        available = bool(available)
        if available == self._available:
            return
        self._available = available
        self.availability_changed.emit(available)

    def _set_condition(self, state: SystemState, enabled: bool) -> None:
        enabled = bool(enabled)
        if self._conditions.get(state, False) == enabled:
            return
        self._conditions[state] = enabled
        self.condition_changed.emit(state, enabled)

    def _on_source_event(self, kind: str, enabled: bool) -> None:
        state = self._EVENT_TO_STATE.get(str(kind).lower())
        if state is None:
            log.debug("Ignoring unknown system-state event: %s", kind)
            return

        terminal_states = {
            SystemState.TRANSITIONING,
            SystemState.SHUTTING_DOWN,
            SystemState.RESTARTING,
        }
        if enabled and state in terminal_states:
            for other in terminal_states - {state}:
                self._set_condition(other, False)
        self._set_condition(state, enabled)
