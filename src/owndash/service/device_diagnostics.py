from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from owndash.core.display import (
    DisplayBusyError,
    DisplayCapabilities,
    DisplayInfo,
    DisplayNotFoundError,
    DisplayProtocolError,
)
from owndash.hardware.usb_setup import (
    UsbAccessStatus,
    probe_artinchip_usb,
    probe_owndash_udev_state,
)


class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"


class DeviceErrorCategory(StrEnum):
    NOT_FOUND = "not_found"
    PERMISSION = "permission"
    BUSY = "busy"
    PROTOCOL = "protocol"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CapabilityDiagnostic:
    key: str
    status: CapabilityStatus


@dataclass(frozen=True, slots=True)
class DeviceDiagnosticSnapshot:
    backend_key: str
    backend_name: str
    connected: bool
    device_detected: bool | None
    accessible: bool | None
    device_node: str | None
    usb_vid_pid: str | None
    device_name: str | None
    native_width: int | None
    native_height: int | None
    refresh_hz: int | None
    rotation: int | None
    output_mode: str
    udev_state: str
    capabilities: tuple[CapabilityDiagnostic, ...]
    last_connected_at: datetime | None
    last_disconnected_at: datetime | None
    last_error_category: DeviceErrorCategory | None
    last_error_message: str | None
    last_known_info: DisplayInfo | None


_CAPABILITY_FIELDS = (
    "hardware_brightness",
    "device_version",
    "panel_info",
    "expansion_mode",
    "startup_image",
    "startup_video",
    "hardware_screen_off",
    "firmware_upgrade",
)

_AIC_UNVERIFIED = {
    "hardware_brightness",
    "device_version",
    "panel_info",
    "expansion_mode",
    "startup_image",
    "startup_video",
    "hardware_screen_off",
}

_SYSTEM_REPORT_KEYS = ("distribution", "kernel", "desktop", "session")


class DeviceDiagnosticsService:
    """Session-lifetime, read-only display diagnostics state."""

    def __init__(
        self,
        *,
        usb_probe: Callable[[], UsbAccessStatus] = probe_artinchip_usb,
        udev_probe: Callable[[], str] = probe_owndash_udev_state,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._usb_probe = usb_probe
        self._udev_probe = udev_probe
        self._clock = clock
        self._last_known_info: DisplayInfo | None = None
        self._last_connected_at: datetime | None = None
        self._last_disconnected_at: datetime | None = None
        self._last_error_category: DeviceErrorCategory | None = None
        self._last_error_message: str | None = None

    def record_connected(self, info: DisplayInfo) -> None:
        self._last_known_info = info
        self._last_connected_at = self._clock()

    def record_disconnected(self) -> None:
        self._last_disconnected_at = self._clock()

    def record_error(self, error: object) -> None:
        self._last_error_message = str(error)
        self._last_error_category = self._classify_error(error)

    def snapshot(
        self,
        *,
        backend_key: str,
        backend_name: str,
        connected: bool,
        current_info: DisplayInfo | None,
        capabilities: DisplayCapabilities,
        output_mode: str,
        rotation: int | None,
    ) -> DeviceDiagnosticSnapshot:
        detected: bool | None = None
        accessible: bool | None = None
        device_node: str | None = None
        usb_vid_pid: str | None = None
        udev_state = "unknown"

        if backend_key == "aic_usb":
            usb_vid_pid = "33C3:0E02"
            try:
                usb = self._usb_probe()
            except Exception:
                usb = None
            if usb is not None:
                detected = bool(usb.connected)
                accessible = bool(usb.accessible)
                device_node = usb.device_node
            try:
                candidate = self._udev_probe()
                if candidate in {"ok", "legacy", "missing", "unknown"}:
                    udev_state = candidate
            except Exception:
                udev_state = "unknown"

        live_info = current_info if connected and current_info is not None else None
        return DeviceDiagnosticSnapshot(
            backend_key=backend_key,
            backend_name=backend_name,
            connected=bool(connected),
            device_detected=detected,
            accessible=accessible,
            device_node=device_node,
            usb_vid_pid=usb_vid_pid,
            device_name=live_info.name if live_info is not None else None,
            native_width=live_info.width if live_info is not None else None,
            native_height=live_info.height if live_info is not None else None,
            refresh_hz=live_info.refresh_hz if live_info is not None else None,
            rotation=rotation,
            output_mode=output_mode,
            udev_state=udev_state,
            capabilities=self._capability_diagnostics(backend_key, capabilities),
            last_connected_at=self._last_connected_at,
            last_disconnected_at=self._last_disconnected_at,
            last_error_category=self._last_error_category,
            last_error_message=self._last_error_message,
            last_known_info=self._last_known_info,
        )

    def _capability_diagnostics(
        self,
        backend_key: str,
        capabilities: DisplayCapabilities,
    ) -> tuple[CapabilityDiagnostic, ...]:
        result = [CapabilityDiagnostic("jpeg_streaming", CapabilityStatus.AVAILABLE)]
        for key in _CAPABILITY_FIELDS:
            if bool(getattr(capabilities, key)):
                status = CapabilityStatus.AVAILABLE
            elif backend_key == "aic_usb" and key in _AIC_UNVERIFIED:
                status = CapabilityStatus.UNVERIFIED
            else:
                status = CapabilityStatus.UNSUPPORTED
            result.append(CapabilityDiagnostic(key, status))
        return tuple(result)

    def _classify_error(self, error: object) -> DeviceErrorCategory:
        try:
            usb = self._usb_probe()
        except Exception:
            usb = None

        if usb is not None and usb.connected and not usb.accessible:
            return DeviceErrorCategory.PERMISSION
        if isinstance(error, PermissionError):
            return DeviceErrorCategory.PERMISSION
        if isinstance(error, DisplayNotFoundError):
            return DeviceErrorCategory.NOT_FOUND
        if isinstance(error, DisplayBusyError):
            return DeviceErrorCategory.BUSY
        if isinstance(error, DisplayProtocolError):
            return DeviceErrorCategory.PROTOCOL

        text = str(error).lower()
        if any(
            marker in text
            for marker in (
                "disconnected",
                "disappeared",
                "removed",
                "no device",
                "enodev",
                "getrennt",
            )
        ):
            return DeviceErrorCategory.DISCONNECTED
        return DeviceErrorCategory.UNKNOWN


def sanitize_diagnostic_text(
    text: str,
    *,
    home: str | None = None,
    username: str | None = None,
) -> str:
    """Remove user-identifying path/name fragments from diagnostic text."""
    result = str(text)
    if home:
        result = result.replace(str(home), "[redacted-home]")
    if username:
        result = result.replace(f"/var/home/{username}", "[redacted-home]")
        result = result.replace(f"/home/{username}", "[redacted-home]")
        result = result.replace(str(username), "[redacted]")
    return result


def _report_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def _report_time(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.isoformat(sep=" ", timespec="seconds")


def format_diagnostic_report(
    snapshot: DeviceDiagnosticSnapshot,
    *,
    app_version: str,
    system_info: dict[str, str] | None = None,
    home: str | None = None,
    username: str | None = None,
) -> str:
    """Format a deterministic, sanitized report suitable for an issue."""
    lines = [
        "OwnDash Device Diagnostic",
        f"OwnDash: {app_version}",
        f"Backend: {snapshot.backend_key} ({snapshot.backend_name})",
        f"Connected: {_report_bool(snapshot.connected)}",
        f"Output: {snapshot.output_mode}",
        f"Rotation: {snapshot.rotation if snapshot.rotation is not None else '—'}",
    ]

    if snapshot.device_name is not None:
        lines.append(f"Device: {snapshot.device_name}")
    if snapshot.native_width is not None and snapshot.native_height is not None:
        lines.append(f"Native: {snapshot.native_width}x{snapshot.native_height}")
    if snapshot.refresh_hz is not None:
        lines.append(f"FPS: {snapshot.refresh_hz}")

    if snapshot.usb_vid_pid is not None:
        lines.extend(
            [
                "",
                "USB:",
                f"VID:PID: {snapshot.usb_vid_pid}",
                f"Detected: {_report_bool(snapshot.device_detected)}",
                f"Access: {_report_bool(snapshot.accessible)}",
                f"Device node: {snapshot.device_node or '—'}",
                f"udev: {snapshot.udev_state}",
            ]
        )

    lines.extend(["", "Capabilities:"])
    lines.extend(f"{item.key}: {item.status.value}" for item in snapshot.capabilities)

    lines.extend(
        [
            "",
            "Last activity:",
            f"Last connected: {_report_time(snapshot.last_connected_at)}",
            f"Last disconnected: {_report_time(snapshot.last_disconnected_at)}",
        ]
    )
    if snapshot.last_known_info is not None:
        info = snapshot.last_known_info
        lines.append(f"Last known device: {info.name} · {info.width}x{info.height}")
    if snapshot.last_error_category is not None:
        lines.append(f"Last error category: {snapshot.last_error_category.value}")
    if snapshot.last_error_message:
        lines.append(f"Last error: {snapshot.last_error_message}")

    if system_info:
        system_lines = []
        for key in _SYSTEM_REPORT_KEYS:
            value = system_info.get(key)
            if value:
                system_lines.append(f"{key}: {value}")
        if system_lines:
            lines.extend(["", "System:", *system_lines])

    return sanitize_diagnostic_text(
        "\n".join(lines).rstrip() + "\n",
        home=home,
        username=username,
    )
