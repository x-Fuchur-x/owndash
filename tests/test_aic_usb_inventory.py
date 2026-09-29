from pathlib import Path

from owndash.hardware.aic_usb_inventory import probe_artinchip_usb_inventory


def _write(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def _make_supported_device(root: Path, name: str, *, bus: int | None = None, dev: int | None = None) -> Path:
    device = root / name
    device.mkdir()
    _write(device / "idVendor", "33c3\n")
    _write(device / "idProduct", "0e02\n")
    if bus is not None:
        _write(device / "busnum", f"{bus}\n")
    if dev is not None:
        _write(device / "devnum", f"{dev}\n")
    return device


def test_inventory_reports_absent_when_supported_device_is_not_present(tmp_path):
    snapshot = probe_artinchip_usb_inventory(tmp_path)

    assert snapshot.status == "absent"
    assert snapshot.sysfs_name is None
    assert snapshot.interfaces == ()
    assert snapshot.match_count == 0
    assert snapshot.ambiguous is False


def test_inventory_collects_interfaces_and_endpoints_without_opening_usb(tmp_path):
    device = _make_supported_device(tmp_path, "1-2", bus=1, dev=6)
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
    assert snapshot.profile_key == "artinchip-33c3-0e02"
    assert snapshot.profile_name == "ArtInChip / VSDISPLAY 33C3:0E02"
    assert snapshot.vid_pid == "33C3:0E02"
    assert snapshot.match_count == 1
    assert snapshot.ambiguous is False
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
    assert [
        (ep.address, ep.attributes, ep.max_packet_size, ep.direction, ep.transfer_type)
        for ep in found.endpoints
    ] == [
        ("01", "02", "0200", "OUT", "Bulk"),
        ("81", "02", "0200", "IN", "Bulk"),
    ]


def test_endpoint_semantics_decode_interrupt_and_isochronous_types(tmp_path):
    _make_supported_device(tmp_path, "3-1")

    interface = tmp_path / "3-1:1.0"
    interface.mkdir()
    for address, attributes in (("83", "03"), ("04", "01")):
        endpoint = interface / f"ep_{address}"
        endpoint.mkdir()
        _write(endpoint / "bEndpointAddress", f"{address}\n")
        _write(endpoint / "bmAttributes", f"{attributes}\n")

    snapshot = probe_artinchip_usb_inventory(tmp_path)
    endpoints = {endpoint.address: endpoint for endpoint in snapshot.interfaces[0].endpoints}

    assert (endpoints["83"].direction, endpoints["83"].transfer_type) == ("IN", "Interrupt")
    assert (endpoints["04"].direction, endpoints["04"].transfer_type) == ("OUT", "Isochronous")


def test_invalid_endpoint_descriptor_values_degrade_to_unknown(tmp_path):
    _make_supported_device(tmp_path, "4-1")

    interface = tmp_path / "4-1:1.0"
    interface.mkdir()
    endpoint = interface / "ep_bad"
    endpoint.mkdir()
    _write(endpoint / "bEndpointAddress", "zz\n")
    _write(endpoint / "bmAttributes", "xx\n")

    snapshot = probe_artinchip_usb_inventory(tmp_path)
    found = snapshot.interfaces[0].endpoints[0]

    assert found.direction is None
    assert found.transfer_type is None


def test_inventory_prefers_exact_33c3_0e02_match(tmp_path):
    other = tmp_path / "1-1"
    other.mkdir()
    _write(other / "idVendor", "33c3\n")
    _write(other / "idProduct", "0e01\n")

    _make_supported_device(tmp_path, "2-3", bus=2, dev=9)

    snapshot = probe_artinchip_usb_inventory(tmp_path)

    assert snapshot.status == "present"
    assert snapshot.sysfs_name == "2-3"
    assert snapshot.device_node == "/dev/bus/usb/002/009"
    assert snapshot.match_count == 1


def test_inventory_reports_multiple_exact_matches_and_selects_representative_deterministically(tmp_path):
    _make_supported_device(tmp_path, "9-9", bus=9, dev=9)
    _make_supported_device(tmp_path, "2-1", bus=2, dev=4)

    snapshot = probe_artinchip_usb_inventory(tmp_path)

    assert snapshot.status == "present"
    assert snapshot.match_count == 2
    assert snapshot.ambiguous is True
    assert snapshot.sysfs_name == "2-1"
    assert snapshot.device_node == "/dev/bus/usb/002/004"


def test_inventory_does_not_count_unverified_same_vendor_products(tmp_path):
    _make_supported_device(tmp_path, "2-1", bus=2, dev=4)
    other = tmp_path / "1-1"
    other.mkdir()
    _write(other / "idVendor", "33c3\n")
    _write(other / "idProduct", "0e01\n")

    snapshot = probe_artinchip_usb_inventory(tmp_path)

    assert snapshot.match_count == 1
    assert snapshot.ambiguous is False
    assert snapshot.sysfs_name == "2-1"


def test_inventory_degrades_sysfs_inspection_errors_to_unknown():
    class BrokenSysfs:
        def is_dir(self):
            return True

        def iterdir(self):
            raise OSError("denied")

    snapshot = probe_artinchip_usb_inventory(BrokenSysfs())

    assert snapshot.status == "unknown"
    assert snapshot.interfaces == ()
    assert snapshot.match_count == 0
    assert snapshot.ambiguous is False
