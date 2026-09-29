from pathlib import Path

from owndash.hardware.usb_setup import _probe_artinchip_usb


def _write(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def _device(root: Path, name: str, *, product: str = "0e02", bus: int = 1, dev: int = 1) -> None:
    path = root / name
    path.mkdir()
    _write(path / "idVendor", "33c3\n")
    _write(path / "idProduct", f"{product}\n")
    _write(path / "busnum", f"{bus}\n")
    _write(path / "devnum", f"{dev}\n")


def test_access_probe_reports_single_verified_match(tmp_path):
    _device(tmp_path, "3-2", bus=3, dev=7)

    status = _probe_artinchip_usb(tmp_path)

    assert status.connected is True
    assert status.device_node == "/dev/bus/usb/003/007"
    assert status.match_count == 1
    assert status.ambiguous is False


def test_access_probe_reports_multiple_matches_and_uses_sorted_representative(tmp_path):
    _device(tmp_path, "9-1", bus=9, dev=3)
    _device(tmp_path, "2-4", bus=2, dev=8)

    status = _probe_artinchip_usb(tmp_path)

    assert status.connected is True
    assert status.device_node == "/dev/bus/usb/002/008"
    assert status.match_count == 2
    assert status.ambiguous is True


def test_access_probe_does_not_count_unverified_same_vendor_product(tmp_path):
    _device(tmp_path, "1-1", product="0e01", bus=1, dev=2)
    _device(tmp_path, "2-4", product="0e02", bus=2, dev=8)

    status = _probe_artinchip_usb(tmp_path)

    assert status.match_count == 1
    assert status.ambiguous is False
    assert status.device_node == "/dev/bus/usb/002/008"
