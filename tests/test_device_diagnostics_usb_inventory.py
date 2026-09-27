from datetime import datetime

from owndash.core.display import DisplayCapabilities
from owndash.hardware.aic_usb_inventory import (
    ArtInChipUsbInventory,
    UsbEndpointInventory,
    UsbInterfaceInventory,
)
from owndash.hardware.usb_setup import UsbAccessStatus
from owndash.service.device_diagnostics import DeviceDiagnosticsService, format_diagnostic_report


def _inventory():
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


def test_aic_snapshot_carries_passive_usb_inventory_into_report():
    inventory = _inventory()
    service = DeviceDiagnosticsService(
        usb_probe=lambda: UsbAccessStatus(True, True, "/dev/bus/usb/001/006"),
        udev_probe=lambda: "ok",
        inventory_probe=lambda: inventory,
        clock=lambda: datetime(2026, 9, 27, 12, 0, 0),
    )

    snapshot = service.snapshot(
        backend_key="aic_usb",
        backend_name="ArtInChip USB",
        connected=False,
        current_info=None,
        capabilities=DisplayCapabilities(),
        output_mode="Direct USB",
        rotation=270,
    )

    assert snapshot.usb_inventory == inventory
    report = format_diagnostic_report(snapshot, app_version="0.14.0b4")
    for expected in (
        "USB inventory:",
        "Inventory state: present",
        "Sysfs device: 1-2",
        "Device class: 00",
        "Interface 1-2:1.0: number=00 alt=00 class=ff subclass=00 protocol=00 driver=—",
        "Endpoint 01: attributes=02 max_packet=0200",
        "Endpoint 81: attributes=02 max_packet=0200",
    ):
        assert expected in report


def test_non_aic_snapshot_does_not_run_usb_inventory_probe():
    def forbidden_inventory_probe():
        raise AssertionError("non-AIC diagnostics must not inspect ArtInChip inventory")

    service = DeviceDiagnosticsService(
        usb_probe=lambda: UsbAccessStatus(False, False, None),
        udev_probe=lambda: "missing",
        inventory_probe=forbidden_inventory_probe,
    )

    snapshot = service.snapshot(
        backend_key="monitor",
        backend_name="Standard Monitor",
        connected=False,
        current_info=None,
        capabilities=DisplayCapabilities(),
        output_mode="Monitor",
        rotation=0,
    )

    assert snapshot.usb_inventory is None
