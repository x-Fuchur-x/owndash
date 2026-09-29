from pathlib import Path

from owndash.core.updates import (
    ReleaseInfo,
    UpdateCheckResult,
    UpdateCheckStatus,
    check_for_updates,
)


ROOT = Path(__file__).resolve().parents[1]
APP_WINDOW = ROOT / "src" / "owndash" / "gui" / "app_window.py"


class _Response:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def test_check_for_updates_distinguishes_current_from_available():
    current = check_for_updates("0.14.0b5", opener=lambda *_args, **_kwargs: _Response(b"[]"))
    assert current == UpdateCheckResult(UpdateCheckStatus.UP_TO_DATE)

    available = check_for_updates(
        "0.14.0b4",
        opener=lambda *_args, **_kwargs: _Response(
            b'[{"tag_name":"v0.14.0-beta.5","html_url":"https://example/release","prerelease":true,"draft":false}]'
        ),
    )
    assert available.status is UpdateCheckStatus.UPDATE_AVAILABLE
    assert available.release == ReleaseInfo(
        "0.14.0b5",
        "v0.14.0-beta.5",
        "https://example/release",
        True,
    )


def test_check_for_updates_distinguishes_expected_network_failure():
    def fail(*_args, **_kwargs):
        raise TimeoutError("offline")

    result = check_for_updates("0.14.0b4", opener=fail)
    assert result == UpdateCheckResult(UpdateCheckStatus.ERROR)


def test_manual_update_check_is_available_and_does_not_depend_on_auto_preference():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert 'QAction("Auf Updates prüfen …", self)' in source
    assert "update_action.triggered.connect(self._check_for_updates_manually)" in source
    assert "def _check_for_updates_manually(self) -> None:" in source
    assert "self._start_update_check(manual=True)" in source


def test_update_check_has_single_in_flight_guard_and_manual_feedback_paths():
    source = APP_WINDOW.read_text(encoding="utf-8")
    assert "self._update_check_in_progress = False" in source
    assert "if self._update_check_in_progress:" in source
    assert "check_for_updates(__version__)" in source
    assert "UpdateCheckStatus.UP_TO_DATE" in source
    assert "UpdateCheckStatus.ERROR" in source
    assert "_show_update_check_feedback" in source
