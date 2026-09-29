from datetime import datetime

from PySide6.QtWidgets import QLabel

from owndash.core.display import DisplayAmbiguousError, DisplayCapabilities
from owndash.gui.display_controls import DeviceCenterWidget
from owndash.hardware.aic_usb_inventory import ArtInChipUsbInventory
from owndash.hardware.usb_setup import UsbAccessStatus
from owndash.service.device_diagnostics import DeviceDiagnosticsService, format_diagnostic_report


def _service(*, count=2, ambiguous=True):
    return DeviceDiagnosticsService(
        usb_probe=lambda: UsbAccessStatus(
            True,
            False,
            "/dev/bus/usb/002/004",
            match_count=count,
            ambiguous=ambiguous,
        ),
        udev_probe=lambda: "ok",
        inventory_probe=lambda: ArtInChipUsbInventory(
            status="present",
            sysfs_name="2-1",
            device_node="/dev/bus/usb/002/004",
            profile_key="artinchip-33c3-0e02",
            profile_name="ArtInChip / VSDISPLAY 33C3:0E02",
            vid_pid="33C3:0E02",
            match_count=count,
            ambiguous=ambiguous,
        ),
        clock=lambda: datetime(2026, 9, 29, 19, 0, 0),
    )


def _snapshot(service):
    return service.snapshot(
        backend_key="aic_usb",
        backend_name="ArtInChip / VSDISPLAY",
        connected=False,
        current_info=None,
        capabilities=DisplayCapabilities(),
        output_mode="Direct USB",
        rotation=270,
    )


def test_aic_snapshot_exposes_verified_profile_and_multi_match_state():
    result = _snapshot(_service())

    assert result.usb_profile_key == "artinchip-33c3-0e02"
    assert result.usb_profile_name == "ArtInChip / VSDISPLAY 33C3:0E02"
    assert result.usb_vid_pid == "33C3:0E02"
    assert result.usb_match_count == 2
    assert result.usb_ambiguous is True


def test_ambiguous_display_error_has_stable_diagnostic_category():
    service = _service()
    service.record_error(DisplayAmbiguousError("Mehrere kompatible USB-Displays gefunden"))

    result = _snapshot(service)

    assert result.last_error_category.value == "ambiguous"


def test_diagnostic_report_includes_profile_and_ambiguity_without_serial_identity():
    report = format_diagnostic_report(_snapshot(_service()), app_version="0.15-dev")

    assert "Profile key: artinchip-33c3-0e02" in report
    assert "Profile: ArtInChip / VSDISPLAY 33C3:0E02" in report
    assert "Matching devices: 2" in report
    assert "Ambiguous: yes" in report
    assert "serial" not in report.lower()


def test_device_center_shows_profile_match_count_and_ambiguity(qapp):
    snapshot = _snapshot(_service())
    controls = DeviceCenterWidget(
        snapshot,
        refresh_snapshot=lambda: snapshot,
        report_text=lambda _snapshot: "",
        translate=lambda text: text,
    )

    profile = controls.findChild(QLabel, "deviceCenterUsbProfile")
    count = controls.findChild(QLabel, "deviceCenterUsbMatchCount")
    ambiguous = controls.findChild(QLabel, "deviceCenterUsbAmbiguous")

    assert profile is not None
    assert count is not None
    assert ambiguous is not None
    assert profile.text() == "ArtInChip / VSDISPLAY 33C3:0E02"
    assert count.text() == "2"
    assert ambiguous.text() == "Ja"
