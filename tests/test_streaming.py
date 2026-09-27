import time

from owndash.core.display import DisplayBackend, DisplayInfo
from owndash.core.streaming import DisplayStreamer


class FakeBackend(DisplayBackend):
    def __init__(self):
        self.frames: list[bytes] = []
        self.closed = False

    def connect(self) -> DisplayInfo:
        return DisplayInfo("Fake", 1920, 480, 60)

    def send_jpeg(self, payload: bytes) -> None:
        self.frames.append(payload)

    def close(self) -> None:
        self.closed = True


def test_streamer_connects_sends_and_closes():
    backend = FakeBackend()
    connected = []
    streamer = DisplayStreamer(backend, on_connected=connected.append)
    streamer.start()
    deadline = time.monotonic() + 1.0
    while not connected and time.monotonic() < deadline:
        time.sleep(0.01)
    assert connected and connected[0].width == 1920
    streamer.submit(b"frame")
    deadline = time.monotonic() + 1.0
    while not backend.frames and time.monotonic() < deadline:
        time.sleep(0.01)
    streamer.stop()
    assert backend.frames == [b"frame"]
    assert backend.closed


def test_streamer_applies_frame_transform_before_backend_send():
    backend = FakeBackend()
    connected = []
    transformed = []

    def transform(payload: bytes) -> bytes:
        transformed.append(payload)
        return b"dimmed:" + payload

    streamer = DisplayStreamer(
        backend,
        on_connected=connected.append,
        frame_transform=transform,
    )
    streamer.start()
    deadline = time.monotonic() + 1.0
    while not connected and time.monotonic() < deadline:
        time.sleep(0.01)
    assert connected

    streamer.submit(b"frame")
    deadline = time.monotonic() + 1.0
    while not backend.frames and time.monotonic() < deadline:
        time.sleep(0.01)
    streamer.stop()

    assert transformed == [b"frame"]
    assert backend.frames == [b"dimmed:frame"]
