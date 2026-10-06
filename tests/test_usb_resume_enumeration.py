from types import SimpleNamespace

import pytest

from owndash.core.display import DisplayAmbiguousError, DisplayNotFoundError
from owndash.hardware import aic_usb
from test_aic_usb_detection import backend_with


def make_usb_tree(tmp_path, addresses):
    for i, (bus, address) in enumerate(addresses):
        p = tmp_path / f'{bus}-{i+1}'
        p.mkdir()
        for name, value in [('idVendor', '33c3'), ('idProduct', '0e02'), ('busnum', str(bus)), ('devnum', str(address))]:
            (p / name).write_text(value)
    return tmp_path


def device(bus, address):
    return SimpleNamespace(bus=bus, address=address)


def test_connect_ignores_removed_address_after_usb_reenumeration(monkeypatch, tmp_path):
    old, current = device(1, 22), device(1, 29)
    root = make_usb_tree(tmp_path, [(1, 29)])
    monkeypatch.setattr(aic_usb, 'SYS_USB_DEVICES', root, raising=False)
    backend, core, util = backend_with(monkeypatch, [old, current])
    current.is_kernel_driver_active = lambda _: False
    current.ctrl_transfer = lambda *args, **kwargs: b''
    for key in ['CTRL_IN', 'CTRL_TYPE_VENDOR', 'CTRL_RECIPIENT_DEVICE']:
        setattr(util, key, 0)
    monkeypatch.setattr(aic_usb, 'parse_display_parameters', lambda _: (1920, 480, 0, 60))
    monkeypatch.setattr(backend, '_authenticate', lambda _: None)
    assert backend.connect().width == 1920
    assert util.claimed == [(current, 0)]


def test_duplicate_entries_at_same_live_address_are_one_physical_device(tmp_path):
    root = make_usb_tree(tmp_path, [(1, 29)])
    current = device(1, 29)
    result = aic_usb._live_usb_matches([current, device(1, 29)], root)
    assert result == (current,)


def test_two_live_displays_still_refused_before_claim(monkeypatch, tmp_path):
    root = make_usb_tree(tmp_path, [(1, 29), (1, 30)])
    monkeypatch.setattr(aic_usb, 'SYS_USB_DEVICES', root, raising=False)
    backend, _, util = backend_with(monkeypatch, [device(1, 22), device(1, 29), device(1, 30)])
    with pytest.raises(DisplayAmbiguousError):
        backend.connect()
    assert util.claimed == []


def test_only_stale_devices_are_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(aic_usb, 'SYS_USB_DEVICES', tmp_path, raising=False)
    backend, _, util = backend_with(monkeypatch, [device(1, 22)])
    with pytest.raises(DisplayNotFoundError):
        backend.connect()
    assert util.claimed == []


def test_unavailable_or_incomplete_sysfs_does_not_guess(tmp_path):
    matches = (device(1, 22), device(1, 29))
    assert aic_usb._live_usb_matches(matches, tmp_path / 'missing') == matches
    root = make_usb_tree(tmp_path, [(1, 29)])
    (root / '1-1' / 'devnum').unlink()
    assert aic_usb._live_usb_matches(matches, root) == matches


def test_unknown_device_addresses_are_not_silently_discarded(tmp_path):
    root = make_usb_tree(tmp_path, [(1, 29)])
    matches = (object(), object())
    assert aic_usb._live_usb_matches(matches, root) == matches


def test_sysfs_proves_two_live_displays_even_when_pyusb_misses_one(monkeypatch, tmp_path):
    root = make_usb_tree(tmp_path, [(1, 29), (1, 30)])
    monkeypatch.setattr(aic_usb, 'SYS_USB_DEVICES', root, raising=False)
    backend, _, util = backend_with(monkeypatch, [device(1, 22), device(1, 29)])
    with pytest.raises(DisplayAmbiguousError):
        backend.connect()
    assert util.claimed == []
