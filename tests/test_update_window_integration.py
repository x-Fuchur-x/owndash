from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_WINDOW = ROOT / "src" / "owndash" / "gui" / "app_window.py"


def test_update_check_is_optional_delayed_and_backgrounded():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "if not self.preferences.check_updates:" in source
    assert "QTimer.singleShot(1500, self._start_update_check)" in source
    assert "Thread(" in source
    assert "daemon=True" in source
    assert "fetch_available_update(__version__)" in source


def test_worker_delivers_result_to_gui_thread_via_signal():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "class UpdateBridge(QObject):" in source
    assert "completed = Signal(object)" in source
    assert "self._update_bridge.completed.connect(self._handle_update_result)" in source
    assert "self._update_bridge.completed.emit(release)" in source


def test_available_update_uses_modeless_release_notification():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "def _show_update_available(self, release: ReleaseInfo) -> None:" in source
    assert "dialog.setModal(False)" in source
    assert "webbrowser.open(release.url)" in source
    assert "self._update_dialog = dialog" in source
