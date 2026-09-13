from __future__ import annotations

from queue import Empty, Full, Queue
from threading import Event, Thread
from typing import Callable

from .display import DisplayBackend, DisplayInfo

StatusCallback = Callable[[str], None]
ConnectedCallback = Callable[[DisplayInfo], None]
ErrorCallback = Callable[[Exception], None]


class DisplayStreamer:
    """Background sender that keeps GUI rendering and USB I/O separated.

    The queue contains at most one frame.  If the USB link is slower than the
    editor, stale frames are discarded instead of building latency.
    """

    def __init__(
        self,
        backend: DisplayBackend,
        *,
        on_status: StatusCallback | None = None,
        on_connected: ConnectedCallback | None = None,
        on_error: ErrorCallback | None = None,
    ):
        self.backend = backend
        self.on_status = on_status or (lambda _message: None)
        self.on_connected = on_connected or (lambda _info: None)
        self.on_error = on_error or (lambda _error: None)
        self._frames: Queue[bytes] = Queue(maxsize=1)
        self._stop = Event()
        self._thread: Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="OwnDash-DisplayStreamer", daemon=True)
        self._thread.start()

    def submit(self, payload: bytes) -> None:
        if not self.running:
            return
        frame = bytes(payload)
        try:
            self._frames.put_nowait(frame)
            return
        except Full:
            pass
        try:
            self._frames.get_nowait()
        except Empty:
            pass
        try:
            self._frames.put_nowait(frame)
        except Full:
            pass

    def stop(self, timeout: float = 2.5) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout)
        if thread is None or not thread.is_alive():
            self.backend.close()
            self._thread = None
        self._clear_queue()

    def _clear_queue(self) -> None:
        while True:
            try:
                self._frames.get_nowait()
            except Empty:
                return

    def _run(self) -> None:
        try:
            self.on_status("Display wird verbunden …")
            info = self.backend.connect()
            self.on_connected(info)
            self.on_status(f"Verbunden · {info.width}×{info.height}")
            while not self._stop.is_set():
                try:
                    frame = self._frames.get(timeout=0.2)
                except Empty:
                    continue
                self.backend.send_jpeg(frame)
        except Exception as exc:
            if not self._stop.is_set():
                self.on_error(exc)
        finally:
            self.backend.close()
