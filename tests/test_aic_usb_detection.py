import pytest

from owndash.core.display import DisplayAmbiguousError, DisplayNotFoundError
from owndash.hardware.aic_usb import AicUsbDisplayBackend
from owndash.hardware.usb_device_profiles import AIC_33C3_0E02


class FakeUsbError(Exception):
    pass


class FakeUsbCore:
    USBError = FakeUsbError

    def __init__(self, devices):
        self.devices = tuple(devices)
        self.find_calls = []

    def find(self, **kwargs):
        self.find_calls.append(kwargs)
        assert kwargs["idVendor"] == AIC_33C3_0E02.vendor_id
        assert kwargs["idProduct"] == AIC_33C3_0E02.product_id
        assert kwargs["find_all"] is True
        return iter(self.devices)


class FakeUsbUtil:
    def __init__(self):
        self.claimed = []

    def claim_interface(self, device, interface):
        self.claimed.append((device, interface))


def backend_with(monkeypatch, devices):
    core = FakeUsbCore(devices)
    util = FakeUsbUtil()
    backend = AicUsbDisplayBackend()
    monkeypatch.setattr(backend, "_legacy_service_active", lambda: False)
    monkeypatch.setattr(backend, "_load_usb", lambda: (core, util))
    return backend, core, util


def test_connect_keeps_existing_not_found_semantics_for_zero_verified_matches(monkeypatch):
    backend, core, util = backend_with(monkeypatch, [])

    with pytest.raises(DisplayNotFoundError, match="kompatibles USB-Display"):
        backend.connect()

    assert len(core.find_calls) == 1
    assert util.claimed == []


def test_connect_refuses_multiple_verified_matches_before_claiming_any_interface(monkeypatch):
    backend, core, util = backend_with(monkeypatch, [object(), object()])

    with pytest.raises(DisplayAmbiguousError, match="Mehrere kompatible USB-Displays"):
        backend.connect()

    assert len(core.find_calls) == 1
    assert util.claimed == []
