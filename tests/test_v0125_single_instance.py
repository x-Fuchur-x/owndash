from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "src/owndash/__main__.py").read_text(encoding="utf-8")
SINGLE = (ROOT / "src/owndash/single_instance.py").read_text(encoding="utf-8")
INIT = (ROOT / "src/owndash/__init__.py").read_text(encoding="utf-8")

def test_version_0125():
    assert '__version__ = "0.14.0 Beta 3"' in INIT

def test_second_launch_exits_before_window_creation():
    notify = MAIN.index("if notify_existing_instance(server_name):")
    window = MAIN.index("window = MainWindow()")
    assert notify < window
    assert "return 0" in MAIN[notify:window]

def test_primary_process_owns_local_server():
    assert "SingleInstanceServer(server_name, app)" in MAIN
    assert "single_instance.listen()" in MAIN

def test_second_launch_requests_activation():
    assert 'ACTIVATE_MESSAGE = b"activate\\n"' in SINGLE
    assert "socket.write(ACTIVATE_MESSAGE)" in SINGLE

def test_existing_window_is_restored_and_focused():
    assert "window.showNormal()" in MAIN
    assert "window.raise_()" in MAIN
    assert "window.activateWindow()" in MAIN
    assert "single_instance.activation_requested.connect(activate_primary_window)" in MAIN

def test_stale_local_socket_is_recovered():
    assert "QLocalServer.removeServer(self.server_name)" in SINGLE

def test_startup_race_is_not_lost():
    assert "self._pending_activation = True" in SINGLE
    assert "single_instance.consume_pending_activation()" in MAIN
