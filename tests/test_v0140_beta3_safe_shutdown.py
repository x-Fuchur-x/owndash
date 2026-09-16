from pathlib import Path
from threading import Event

from owndash.core.display import DisplayInfo
from owndash.core.streaming import DisplayStreamer


ROOT = Path(__file__).resolve().parents[1]
ENTRY = (ROOT / "src" / "owndash" / "__main__.py").read_text(encoding="utf-8")
APP_WINDOW = ROOT / "src" / "owndash" / "gui" / "app_window.py"


class RecordingBackend:
    def __init__(self):
        self.frames: list[bytes] = []
        self.closed = Event()

    def connect(self) -> DisplayInfo:
        return DisplayInfo("test", 480, 1920, 60)

    def send_jpeg(self, payload: bytes) -> None:
        self.frames.append(bytes(payload))

    def close(self) -> None:
        self.closed.set()


def test_streamer_can_confirm_final_frame_before_shutdown():
    backend = RecordingBackend()
    connected = Event()
    streamer = DisplayStreamer(backend, on_connected=lambda _info: connected.set())
    streamer.start()
    assert connected.wait(1.0)

    assert streamer.submit_final(b"shutdown", timeout=1.0) is True
    streamer.stop()

    assert backend.frames[-1] == b"shutdown"
    assert backend.closed.is_set()


def test_application_uses_safe_shutdown_window():
    assert "from owndash.gui.app_window import SafeShutdownWindow as MainWindow" in ENTRY
    assert "window = MainWindow()" in ENTRY


def test_safe_shutdown_window_uses_official_icon_and_only_runs_on_real_quit():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "class SafeShutdownWindow(MainWindow):" in source
    assert "with app_icon_path() as icon_path:" in source
    assert "streamer.submit_final(payload" in source
    assert "super().closeEvent(event)" in source
    assert "will_hide_to_tray" in source
    assert "if not will_hide_to_tray:" in source
    assert "def _quit_from_tray(self) -> None:" in source
