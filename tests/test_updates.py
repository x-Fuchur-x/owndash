from __future__ import annotations

import io
import json
from urllib.error import URLError

from owndash.core.updates import (
    ReleaseInfo,
    fetch_available_update,
    normalize_version,
    select_newer_release,
)
from owndash.project_info import GITHUB_RELEASES_API_URL


def test_normalizes_internal_and_github_beta_versions():
    assert normalize_version("0.14.0b3") == (0, 14, 0, 3)
    assert normalize_version("0.14.0 Beta 3") == (0, 14, 0, 3)
    assert normalize_version("v0.14.0-beta.3") == (0, 14, 0, 3)
    assert normalize_version("v0.14.0") == (0, 14, 0, None)
    assert normalize_version("garbage") is None


def test_beta_can_see_newer_beta_and_final_release():
    releases = [
        {"tag_name": "v0.14.0-beta.4", "html_url": "https://example/b4", "prerelease": True, "draft": False},
        {"tag_name": "v0.14.0", "html_url": "https://example/final", "prerelease": False, "draft": False},
    ]
    result = select_newer_release("0.14.0b3", releases)
    assert result == ReleaseInfo("0.14.0", "v0.14.0", "https://example/final", False)


def test_equal_or_older_release_is_ignored():
    releases = [
        {"tag_name": "v0.14.0-beta.3", "html_url": "https://example/equal", "prerelease": True, "draft": False},
        {"tag_name": "v0.14.0-beta.2", "html_url": "https://example/old", "prerelease": True, "draft": False},
    ]
    assert select_newer_release("0.14.0b3", releases) is None


def test_stable_ignores_prerelease_even_when_base_version_is_newer():
    releases = [
        {"tag_name": "v0.15.0-beta.1", "html_url": "https://example/b1", "prerelease": True, "draft": False},
    ]
    assert select_newer_release("0.14.0", releases) is None


def test_drafts_and_malformed_entries_are_ignored():
    releases = [
        {"tag_name": "v9.0.0", "html_url": "https://example/draft", "prerelease": False, "draft": True},
        {"tag_name": "nonsense", "html_url": "https://example/bad", "prerelease": False, "draft": False},
        "not-a-dict",
    ]
    assert select_newer_release("0.14.0b3", releases) is None


class _Response:
    def __init__(self, payload: object):
        self._bytes = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._bytes


def test_fetch_uses_official_endpoint_timeout_and_selects_release():
    seen: dict[str, object] = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["user_agent"] = request.headers.get("User-agent")
        return _Response([
            {"tag_name": "v0.14.0-beta.4", "html_url": "https://example/release", "prerelease": True, "draft": False}
        ])

    result = fetch_available_update("0.14.0b3", opener=opener)
    assert result is not None
    assert result.tag == "v0.14.0-beta.4"
    assert seen["url"] == GITHUB_RELEASES_API_URL
    assert seen["timeout"] == 4.0
    assert str(seen["user_agent"]).startswith("OwnDash/")


def test_fetch_returns_none_for_network_and_decode_failures():
    def network_error(_request, _timeout):
        raise URLError("offline")

    def malformed_json(_request, _timeout):
        class BadResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"not-json"
        return BadResponse()

    assert fetch_available_update("0.14.0b3", opener=network_error) is None
    assert fetch_available_update("0.14.0b3", opener=malformed_json) is None
