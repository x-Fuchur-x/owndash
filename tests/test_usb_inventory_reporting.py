from owndash.hardware.aic_usb_inventory import (
    ArtInChipUsbInventory,
    UsbEndpointInventory,
    UsbInterfaceInventory,
)
from owndash.service.device_diagnostics import (
    DeviceDiagnosticSnapshot,
    format_diagnostic_report,
)


def test_diagnostic_report_includes_decoded_endpoint_semantics():
    inventory = ArtInChipUsbInventory(
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
                    UsbEndpointInventory("01", "02", "0200", "OUT", "Bulk"),
                    UsbEndpointInventory("81", "02", "0200", "IN", "Bulk"),
                ),
            ),
        ),
    )
    snapshot = DeviceDiagnosticSnapshot(
        backend_key="aic_usb",
        backend_name="ArtInChip USB",
        connected=False,
        device_detected=True,
        accessible=True,
        device_node="/dev/bus/usb/001/006",
        usb_vid_pid="33C3:0E02",
        device_name=None,
        native_width=None,
        native_height=None,
        refresh_hz=None,
        rotation=270,
        output_mode="Direct USB",
        udev_state="ok",
        capabilities=(),
        last_connected_at=None,
        last_disconnected_at=None,
        last_error_category=None,
        last_error_message=None,
        last_known_info=None,
        usb_inventory=inventory,
    )

    report = format_diagnostic_report(snapshot, app_version="test")

    assert "Endpoint 01: direction=OUT type=Bulk attributes=02 max_packet=0200" in report
    assert "Endpoint 81: direction=IN type=Bulk attributes=02 max_packet=0200" in report
