from pathlib import Path

from owndash.hardware.aic_usb_inventory import probe_artinchip_usb_inventory


def _write(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def test_inventory_reports_absent_when_supported_device_is_not_present(tmp_path):
    snapshot = probe_artinchip_usb_inventory(tmp_path)

    assert snapshot.status == "absent"
    assert snapshot.sysfs_name is None
    assert snapshot.interfaces == ()


def test_inventory_collects_interfaces_and_endpoints_without_opening_usb(tmp_path):
    device = tmp_path / "1-2"
    device.mkdir()
    _write(device / "idVendor", "33c3\n")
    _write(device / "idProduct", "0e02\n")
    _write(device / "busnum", "1\n")
    _write(device / "devnum", "6\n")
    _write(device / "bDeviceClass", "00\n")

    interface = tmp_path / "1-2:1.0"
    interface.mkdir()
    _write(interface / "bInterfaceNumber", "00\n")
    _write(interface / "bAlternateSetting", "00\n")
    _write(interface / "bInterfaceClass", "ff\n")
    _write(interface / "bInterfaceSubClass", "00\n")
    _write(interface / "bInterfaceProtocol", "00\n")

    endpoint_out = interface / "ep_01"
    endpoint_out.mkdir()
    _write(endpoint_out / "bEndpointAddress", "01\n")
    _write(endpoint_out / "bmAttributes", "02\n")
    _write(endpoint_out / "wMaxPacketSize", "0200\n")

    endpoint_in = interface / "ep_81"
    endpoint_in.mkdir()
    _write(endpoint_in / "bEndpointAddress", "81\n")
    _write(endpoint_in / "bmAttributes", "02\n")
    _write(endpoint_in / "wMaxPacketSize", "0200\n")

    snapshot = probe_artinchip_usb_inventory(tmp_path)

    assert snapshot.status == "present"
    assert snapshot.sysfs_name == "1-2"
    assert snapshot.busnum == 1
    assert snapshot.devnum == 6
    assert snapshot.device_node == "/dev/bus/usb/001/006"
    assert snapshot.device_class == "00"
    assert len(snapshot.interfaces) == 1

    found = snapshot.interfaces[0]
    assert found.name == "1-2:1.0"
    assert found.number == "00"
    assert found.alternate_setting == "00"
    assert found.class_code == "ff"
    assert found.subclass_code == "00"
    assert found.protocol_code == "00"
    assert found.driver is None
    assert [(ep.address, ep.attributes, ep.max_packet_size) for ep in found.endpoints] == [
        ("01", "02", "0200"),
        ("81", "02", "0200"),
    ]


def test_inventory_prefers_exact_33c3_0e02_match(tmp_path):
    other = tmp_path / "1-1"
    other.mkdir()
    _write(other / "idVendor", "33c3\n")
    _write(other / "idProduct", "0e01\n")

    supported = tmp_path / "2-3"
    supported.mkdir()
    _write(supported / "idVendor", "33c3\n")
    _write(supported / "idProduct", "0e02\n")
    _write(supported / "busnum", "2\n")
    _write(supported / "devnum", "9\n")

    snapshot = probe_artinchip_usb_inventory(tmp_path)

    assert snapshot.status == "present"
    assert snapshot.sysfs_name == "2-3"
    assert snapshot.device_node == "/dev/bus/usb/002/009"


def test_inventory_degrades_sysfs_inspection_errors_to_unknown():
    class BrokenSysfs:
        def is_dir(self):
            return True

        def iterdir(self):
            raise OSError("denied")

    snapshot = probe_artinchip_usb_inventory(BrokenSysfs())

    assert snapshot.status == "unknown"
    assert snapshot.interfaces == ()
