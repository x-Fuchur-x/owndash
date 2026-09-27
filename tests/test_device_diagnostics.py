from __future__ import annotations

from datetime import datetime
import importlib
import importlib.util

import pytest

from owndash.core.display import (
    DisplayBusyError,
    DisplayCapabilities,
    DisplayInfo,
    DisplayNotFoundError,
    DisplayProtocolError,
)
from owndash.hardware.usb_setup import UsbAccessStatus


def diagnostics_module():
    spec = importlib.util.find_spec("owndash.service.device_diagnostics")
    assert spec is not None, "device diagnostics service module must exist"
    return importlib.import_module("owndash.service.device_diagnostics")


def make_service(*, usb_status=UsbAccessStatus(False, False, None), udev_state="missing", clock=None):
    module = diagnostics_module()
    return module.DeviceDiagnosticsService(
        usb_probe=lambda: usb_status,
        udev_probe=lambda: udev_state,
        clock=clock or (lambda: datetime(2026, 9, 27, 12, 0, 0)),
    )


def snapshot(service, **overrides):
    values = dict(
        backend_key="aic_usb",
        backend_name="ArtInChip USB",
        connected=False,
        current_info=None,
        capabilities=DisplayCapabilities(),
        output_mode="Direct USB",
        rotation=270,
    )
    values.update(overrides)
    return service.snapshot(**values)


def capability_map(result):
    return {item.key: item.status.value for item in result.capabilities}


def test_snapshot_without_detected_device_is_coherent():
    result = snapshot(make_service())
    assert result.backend_key == "aic_usb"
    assert result.connected is False
    assert result.device_detected is False
    assert result.accessible is False
    assert result.device_node is None
    assert result.usb_vid_pid == "33C3:0E02"
    assert result.device_name is None


def test_snapshot_detected_but_inaccessible_device():
    service = make_service(
        usb_status=UsbAccessStatus(True, False, "/dev/bus/usb/001/006"),
        udev_state="missing",
    )
    result = snapshot(service)
    assert result.device_detected is True
    assert result.accessible is False
    assert result.device_node == "/dev/bus/usb/001/006"
    assert result.udev_state == "missing"


def test_snapshot_detected_and_accessible_device():
    service = make_service(
        usb_status=UsbAccessStatus(True, True, "/dev/bus/usb/001/006"),
        udev_state="ok",
    )
    result = snapshot(service)
    assert result.device_detected is True
    assert result.accessible is True
    assert result.udev_state == "ok"


def test_snapshot_probe_failure_degrades_to_unknown_live_state():
    module = diagnostics_module()

    def fail_probe():
        raise OSError("sysfs changed")

    service = module.DeviceDiagnosticsService(
        usb_probe=fail_probe,
        udev_probe=lambda: "unknown",
        clock=lambda: datetime(2026, 9, 27, 12, 0, 0),
    )
    result = snapshot(service)
    assert result.device_detected is None
    assert result.accessible is None
    assert result.device_node is None
    assert result.udev_state == "unknown"


def test_connection_and_disconnect_retain_last_known_device():
    times = iter(
        [
            datetime(2026, 9, 27, 12, 1, 0),
            datetime(2026, 9, 27, 12, 2, 0),
        ]
    )
    service = make_service(clock=lambda: next(times))
    info = DisplayInfo("USB Bar Display", 1920, 480, 30)

    service.record_connected(info)
    service.record_disconnected()
    result = snapshot(service)

    assert result.last_known_info == info
    assert result.last_connected_at == datetime(2026, 9, 27, 12, 1, 0)
    assert result.last_disconnected_at == datetime(2026, 9, 27, 12, 2, 0)


def test_reconnect_replaces_last_known_device():
    times = iter(
        [
            datetime(2026, 9, 27, 12, 1, 0),
            datetime(2026, 9, 27, 12, 3, 0),
        ]
    )
    service = make_service(clock=lambda: next(times))
    service.record_connected(DisplayInfo("Old", 800, 480, 30))
    new_info = DisplayInfo("USB Bar Display", 1920, 480, 30)
    service.record_connected(new_info)
    result = snapshot(service, connected=True, current_info=new_info)

    assert result.last_known_info == new_info
    assert result.device_name == "USB Bar Display"
    assert (result.native_width, result.native_height, result.refresh_hz) == (1920, 480, 30)
    assert result.last_connected_at == datetime(2026, 9, 27, 12, 3, 0)


def test_backend_change_keeps_old_aic_information_historical_only():
    service = make_service()
    old_info = DisplayInfo("USB Bar Display", 1920, 480, 30)
    service.record_connected(old_info)

    result = snapshot(
        service,
        backend_key="monitor",
        backend_name="Standard Monitor",
        connected=False,
        current_info=None,
        output_mode="Monitor",
        rotation=0,
    )

    assert result.backend_key == "monitor"
    assert result.device_detected is None
    assert result.accessible is None
    assert result.usb_vid_pid is None
    assert result.device_name is None
    assert result.last_known_info == old_info


def test_aic_capability_policy_distinguishes_unverified_from_unsupported():
    module = diagnostics_module()
    result = snapshot(make_service())
    caps = capability_map(result)

    assert caps["jpeg_streaming"] == module.CapabilityStatus.AVAILABLE.value
    for key in (
        "hardware_brightness",
        "device_version",
        "panel_info",
        "expansion_mode",
        "startup_image",
        "startup_video",
        "hardware_screen_off",
    ):
        assert caps[key] == module.CapabilityStatus.UNVERIFIED.value
    assert caps["firmware_upgrade"] == module.CapabilityStatus.UNSUPPORTED.value


def test_exposed_backend_capability_is_available():
    result = snapshot(
        make_service(),
        capabilities=DisplayCapabilities(hardware_brightness=True, expansion_mode=True),
    )
    caps = capability_map(result)
    assert caps["hardware_brightness"] == "available"
    assert caps["expansion_mode"] == "available"


def test_non_aic_absent_optional_capabilities_are_unsupported():
    result = snapshot(
        make_service(),
        backend_key="monitor",
        backend_name="Standard Monitor",
        output_mode="Monitor",
        rotation=0,
    )
    caps = capability_map(result)
    assert caps["jpeg_streaming"] == "available"
    assert caps["hardware_brightness"] == "unsupported"
    assert caps["expansion_mode"] == "unsupported"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (DisplayNotFoundError("missing"), "not_found"),
        (DisplayBusyError("busy"), "busy"),
        (DisplayProtocolError("authentication failed"), "protocol"),
        (RuntimeError("USB display disconnected during transfer"), "disconnected"),
        (RuntimeError("USB disappeared during suspend"), "disconnected"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
def test_error_classification(error, expected):
    service = make_service()
    service.record_error(error)
    result = snapshot(service)
    assert result.last_error_category.value == expected
    assert result.last_error_message == str(error)


def test_inaccessible_probe_overrides_generic_protocol_error_as_permission():
    service = make_service(usb_status=UsbAccessStatus(True, False, "/dev/bus/usb/001/006"))
    service.record_error(DisplayProtocolError("USB open failed"))
    result = snapshot(service)
    assert result.last_error_category.value == "permission"


def test_diagnostic_report_contains_whitelisted_device_and_system_facts():
    module = diagnostics_module()
    formatter = getattr(module, "format_diagnostic_report", None)
    assert callable(formatter)
    service = make_service(
        usb_status=UsbAccessStatus(True, True, "/dev/bus/usb/001/006"),
        udev_state="ok",
    )
    info = DisplayInfo("USB Bar Display", 1920, 480, 30)
    service.record_connected(info)
    result = snapshot(service, connected=True, current_info=info)

    report = formatter(
        result,
        app_version="0.14.0b4",
        system_info={
            "distribution": "Bazzite",
            "kernel": "6.17-test",
            "desktop": "KDE Plasma",
            "session": "Wayland",
            "secret": "must-not-appear",
        },
    )

    for expected in (
        "OwnDash Device Diagnostic",
        "0.14.0b4",
        "aic_usb",
        "ArtInChip USB",
        "Direct USB",
        "270",
        "USB Bar Display",
        "1920x480",
        "30",
        "33C3:0E02",
        "/dev/bus/usb/001/006",
        "udev: ok",
        "hardware_brightness: unverified",
        "firmware_upgrade: unsupported",
        "Bazzite",
        "KDE Plasma",
        "Wayland",
    ):
        assert expected in report
    assert "must-not-appear" not in report


def test_diagnostic_report_sanitizes_user_identity_and_home_paths_but_keeps_device_node():
    module = diagnostics_module()
    formatter = getattr(module, "format_diagnostic_report", None)
    sanitizer = getattr(module, "sanitize_diagnostic_text", None)
    assert callable(formatter)
    assert callable(sanitizer)

    service = make_service(
        usb_status=UsbAccessStatus(True, True, "/dev/bus/usb/001/006"),
        udev_state="ok",
    )
    service.record_error(
        RuntimeError("failed /home/alice/private.txt and /var/home/alice/config for alice")
    )
    result = snapshot(service)
    report = formatter(
        result,
        app_version="0.14.0b4",
        home="/home/alice",
        username="alice",
    )

    assert "alice" not in report
    assert "/home/alice" not in report
    assert "/var/home/alice" not in report
    assert "/dev/bus/usb/001/006" in report
    assert "[redacted]" in report
