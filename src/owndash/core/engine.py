from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from time import monotonic, sleep
from typing import Callable


@dataclass(slots=True)
class EngineSettings:
    fps: float = 2.0


class RenderEngine:
    def __init__(self, render_frame: Callable[[], bytes], send_frame: Callable[[bytes], None], settings: EngineSettings | None = None):
        self.render_frame = render_frame
        self.send_frame = send_frame
        self.settings = settings or EngineSettings()
        self._stop = Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        interval = 1.0 / max(0.1, self.settings.fps)
        while not self._stop.is_set():
            started = monotonic()
            self.send_frame(self.render_frame())
            remaining = interval - (monotonic() - started)
            if remaining > 0:
                sleep(remaining)
