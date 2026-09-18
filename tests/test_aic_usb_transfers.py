import errno
import struct

import pytest
from usb.core import USBError

from owndash.core.display import DisplayProtocolError
from owndash.hardware.aic_usb import AicUsbDisplayBackend, UsbBackendSettings


class UsbDevice:
    """USB boundary double: record packets and inject transfer outcomes."""

    def __init__(self, outcomes=()):
        self.outcomes = iter(outcomes)
        self.packets = []
        self.halts = []

    def write(self, endpoint, payload, timeout):
        assert endpoint == 0x01
        self.packets.append(bytes(payload))
        result = next(self.outcomes, len(payload))
        if isinstance(result, Exception):
            raise result
        return result

    def clear_halt(self, endpoint):
        self.halts.append(endpoint)


def backend_for(device):
    backend = AicUsbDisplayBackend(UsbBackendSettings(rotation=0, block_size=4096))
    backend._dev = device
    backend._usb_util = object()
    return backend


def test_header_stall_retry_sends_complete_frame():
    device = UsbDevice([USBError('pipe stalled', errno=errno.EPIPE)])
    backend = backend_for(device)
    backend.send_jpeg(b'frame')
    header = struct.pack('<IIHHII', 0xA1C62B01, 5, 0, 0, 0, 0xA1C62B01)
    assert device.packets == [header, header, b'frame']
    assert backend._frame_id == 1


@pytest.mark.parametrize('written', [0, 19])
def test_short_header_is_rejected_without_replaying(written):
    device = UsbDevice([written])
    backend = backend_for(device)
    with pytest.raises(DisplayProtocolError, match='USB'):
        backend.send_jpeg(b'frame')
    assert len(device.packets) == 1
    assert device.halts == []
    assert backend._frame_id == 0


@pytest.mark.parametrize('written', [0, 4])
def test_short_payload_is_rejected_without_replaying(written):
    device = UsbDevice([20, written])
    backend = backend_for(device)
    with pytest.raises(DisplayProtocolError, match='USB'):
        backend.send_jpeg(b'frame')
    assert len(device.packets) == 2
    assert device.halts == []
    assert backend._frame_id == 0


def test_disconnect_does_not_clear_halt_or_replay():
    device = UsbDevice([USBError('device gone', errno=errno.ENODEV)])
    backend = backend_for(device)
    with pytest.raises(DisplayProtocolError, match='USB'):
        backend.send_jpeg(b'frame')
    assert len(device.packets) == 1
    assert device.halts == []
    assert backend._frame_id == 0


def test_successful_multiblock_frame_and_sequence_wrap():
    device = UsbDevice()
    backend = backend_for(device)
    backend._frame_id = 65535
    backend.send_jpeg(b'x' * 4097)
    assert device.packets == [
        struct.pack('<IIHHII', 0xA1C62B01, 4097, 65535, 0, 0, 0xA1C62B01),
        b'x' * 4096, b'x',
    ]
    assert backend._frame_id == 0


def test_persistent_stall_stops_after_one_retry():
    device = UsbDevice([USBError('stall', errno=errno.EPIPE)] * 2)
    backend = backend_for(device)
    with pytest.raises(DisplayProtocolError):
        backend.send_jpeg(b'frame')
    assert len(device.packets) == 2
    assert device.halts == [0x01]
    assert backend._frame_id == 0
