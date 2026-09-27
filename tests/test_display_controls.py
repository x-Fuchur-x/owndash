import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QGroupBox, QLabel, QPushButton, QSlider

import owndash.gui.display_controls as display_controls
from owndash.core.display import DisplayInfo
from owndash.hardware.aic_usb_inventory import (
    ArtInChipUsbInventory,
    UsbEndpointInventory,
    UsbInterfaceInventory,
)
from owndash.service.device_diagnostics import (
    CapabilityDiagnostic,
    CapabilityStatus,
    DeviceDiagnosticSnapshot,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def sample_inventory():
    return ArtInChipUsbInventory(
        status="present",
        sysfs_name="1-2",
        busnum=1,
        devnum=6,
        device_node="/dev/bus/usb/001/006",
        device_class="00",
        interfaces=(
            UsbInterfaceInventory(
                name="1-2:1.0",
                number="00",
                alternate_setting="00",
                class_code="ff",
                subclass_code="00",
                protocol_code="00",
                driver=None,
                endpoints=(
                    UsbEndpointInventory("01", "02", "0200"),
                    UsbEndpointInventory("81", "02", "0200"),
                ),
            ),
        ),
    )


def make_snapshot(*, connected=False, device_name=None, last_known=True, usb_inventory=None):
    info = DisplayInfo("USB Bar Display", 1920, 480, 30) if last_known else None
    if usb_inventory is None:
        usb_inventory = sample_inventory()
    return DeviceDiagnosticSnapshot(
        backend_key="aic_usb",
        backend_name="ArtInChip USB",
        connected=connected,
        device_detected=True,
        accessible=True,
        device_node="/dev/bus/usb/001/006",
        usb_vid_pid="33C3:0E02",
        device_name=device_name,
        native_width=1920 if device_name else None,
        native_height=480 if device_name else None,
        refresh_hz=30 if device_name else None,
        rotation=270,
        output_mode="Direct USB",
        udev_state="ok",
        capabilities=(
            CapabilityDiagnostic("jpeg_streaming", CapabilityStatus.AVAILABLE),
            CapabilityDiagnostic("hardware_brightness", CapabilityStatus.UNVERIFIED),
            CapabilityDiagnostic("firmware_upgrade", CapabilityStatus.UNSUPPORTED),
        ),
        last_connected_at=datetime(2026, 9, 27, 12, 1, 0),
        last_disconnected_at=datetime(2026, 9, 27, 12, 2, 0),
        last_error_category=None,
        last_error_message=None,
        last_known_info=info,
        usb_inventory=usb_inventory,
    )


def build_widget(app, snapshot=None, refresh_snapshot=None, report_text=None):
    widget_class = getattr(display_controls, "DeviceCenterWidget", None)
    assert widget_class is not None, "DeviceCenterWidget must replace hardware controls"
    widget = widget_class(
        snapshot or make_snapshot(),
        refresh_snapshot=refresh_snapshot or (lambda: snapshot or make_snapshot()),
        report_text=report_text or (lambda _snapshot: "diagnostic report"),
    )
    widget.show()
    app.processEvents()
    return widget


def test_device_center_renders_five_read_only_sections(app):
    widget = build_widget(app)
    try:
        expected = {
            "deviceCenterDeviceSection": "Gerät",
            "deviceCenterUsbSection": "USB & Zugriff",
            "deviceCenterUsbInventorySection": "USB-Inventar",
            "deviceCenterCapabilitiesSection": "Funktionen",
            "deviceCenterActivitySection": "Letzte Aktivität",
        }
        for object_name, title in expected.items():
            group = widget.findChild(QGroupBox, object_name)
            assert group is not None
            assert group.title() == title
        assert widget.findChildren(QSlider) == []
        assert widget.findChildren(QCheckBox) == []
    finally:
        widget.close()


def test_usb_inventory_section_shows_passive_sysfs_evidence(app):
    widget = build_widget(app)
    try:
        status = widget.findChild(QLabel, "deviceCenterUsbInventoryStatus")
        sysfs = widget.findChild(QLabel, "deviceCenterUsbInventorySysfs")
        device_class = widget.findChild(QLabel, "deviceCenterUsbInventoryDeviceClass")
        details = widget.findChild(QLabel, "deviceCenterUsbInventoryDetails")
        assert status is not None and status.text() == "Vorhanden"
        assert sysfs is not None and sysfs.text() == "1-2"
        assert device_class is not None and device_class.text() == "00"
        assert details is not None
        for expected in (
            "1-2:1.0",
            "Klasse ff",
            "Treiber —",
            "EP 01 · Attr 02 · Max 0200",
            "EP 81 · Attr 02 · Max 0200",
        ):
            assert expected in details.text()
    finally:
        widget.close()


def test_usb_inventory_unknown_state_is_explicit(app):
    snapshot = make_snapshot(usb_inventory=ArtInChipUsbInventory(status="unknown"))
    widget = build_widget(app, snapshot)
    try:
        status = widget.findChild(QLabel, "deviceCenterUsbInventoryStatus")
        details = widget.findChild(QLabel, "deviceCenterUsbInventoryDetails")
        assert status is not None and status.text() == "Unbekannt"
        assert details is not None and details.text() == "—"
    finally:
        widget.close()


def test_disconnected_state_keeps_last_known_device_visible(app):
    widget = build_widget(app, make_snapshot(connected=False, device_name=None))
    try:
        status = widget.findChild(QLabel, "deviceCenterConnectionStatus")
        last_known = widget.findChild(QLabel, "deviceCenterLastKnown")
        assert status is not None and status.text() == "Nicht verbunden"
        assert last_known is not None
        assert "USB Bar Display" in last_known.text()
        assert "1920×480" in last_known.text()
    finally:
        widget.close()


def test_capability_states_are_distinct_and_explicit(app):
    widget = build_widget(app)
    try:
        available = widget.findChild(QLabel, "deviceCenterCapability_jpeg_streaming")
        unverified = widget.findChild(QLabel, "deviceCenterCapability_hardware_brightness")
        unsupported = widget.findChild(QLabel, "deviceCenterCapability_firmware_upgrade")
        assert available is not None and available.text() == "Verfügbar"
        assert unverified is not None and unverified.text() == "Noch nicht verifiziert"
        assert unsupported is not None and unsupported.text() == "Nicht unterstützt"
    finally:
        widget.close()


def test_refresh_replaces_snapshot_without_hardware_reference(app):
    calls = []
    refreshed = make_snapshot(connected=True, device_name="USB Bar Display")

    def refresh():
        calls.append(True)
        return refreshed

    widget = build_widget(app, make_snapshot(), refresh_snapshot=refresh)
    try:
        button = widget.findChild(QPushButton, "deviceCenterRefreshButton")
        assert button is not None
        QTest.mouseClick(button, Qt.LeftButton)
        app.processEvents()
        status = widget.findChild(QLabel, "deviceCenterConnectionStatus")
        device = widget.findChild(QLabel, "deviceCenterDeviceName")
        assert calls == [True]
        assert status is not None and status.text() == "Verbunden"
        assert device is not None and device.text() == "USB Bar Display"
        assert not hasattr(widget, "backend")
    finally:
        widget.close()


def test_copy_diagnostic_report_uses_current_snapshot(app):
    copied = []

    def report(current):
        copied.append(current.connected)
        return "OwnDash Device Diagnostic\nconnected=no\n"

    widget = build_widget(app, make_snapshot(connected=False), report_text=report)
    try:
        button = widget.findChild(QPushButton, "deviceCenterCopyButton")
        assert button is not None
        QApplication.clipboard().clear()
        QTest.mouseClick(button, Qt.LeftButton)
        app.processEvents()
        assert copied == [False]
        assert QApplication.clipboard().text() == "OwnDash Device Diagnostic\nconnected=no\n"
    finally:
        widget.close()
