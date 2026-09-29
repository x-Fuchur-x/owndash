from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import re
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from owndash.project_info import GITHUB_RELEASES_API_URL


VersionTuple = tuple[int, int, int, int | None]

_VERSION_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:(?:[- ]?beta[ .-]?|b)(?P<beta>\d+))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    tag: str
    url: str
    prerelease: bool


class UpdateCheckStatus(StrEnum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    status: UpdateCheckStatus
    release: ReleaseInfo | None = None


def normalize_version(value: str) -> VersionTuple | None:
    """Normalize OwnDash display versions and GitHub tags.

    Supported examples include ``0.14.0``, ``0.14.0b3``,
    ``0.14.0 Beta 3`` and ``v0.14.0-beta.3``.
    """
    match = _VERSION_RE.fullmatch(str(value).strip())
    if match is None:
        return None
    beta_text = match.group("beta")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        int(beta_text) if beta_text is not None else None,
    )


def _version_key(version: VersionTuple) -> tuple[int, int, int, int, int]:
    major, minor, patch, beta = version
    # A final release sorts after every beta of the same base version.
    return major, minor, patch, 1 if beta is None else 0, beta if beta is not None else 0


def _canonical_version(version: VersionTuple) -> str:
    major, minor, patch, beta = version
    base = f"{major}.{minor}.{patch}"
    return base if beta is None else f"{base}b{beta}"


def select_newer_release(current_version: str, releases: list[object]) -> ReleaseInfo | None:
    """Return the newest eligible release newer than ``current_version``."""
    current = normalize_version(current_version)
    if current is None:
        return None

    current_is_prerelease = current[3] is not None
    current_key = _version_key(current)
    candidates: list[tuple[tuple[int, int, int, int, int], ReleaseInfo]] = []

    for raw in releases:
        if not isinstance(raw, dict) or bool(raw.get("draft", False)):
            continue

        tag = raw.get("tag_name")
        url = raw.get("html_url")
        if not isinstance(tag, str) or not isinstance(url, str) or not url:
            continue

        parsed = normalize_version(tag)
        if parsed is None:
            continue

        prerelease = bool(raw.get("prerelease", False)) or parsed[3] is not None
        if not current_is_prerelease and prerelease:
            continue

        key = _version_key(parsed)
        if key <= current_key:
            continue

        candidates.append(
            (
                key,
                ReleaseInfo(
                    version=_canonical_version(parsed),
                    tag=tag,
                    url=url,
                    prerelease=prerelease,
                ),
            )
        )

    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _release_request(current_version: str) -> Request:
    return Request(
        GITHUB_RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"OwnDash/{current_version}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def check_for_updates(
    current_version: str,
    *,
    opener: Callable[..., object] = urlopen,
    timeout: float = 4.0,
) -> UpdateCheckResult:
    """Check official release metadata and preserve the outcome category.

    This richer result is used by user-initiated checks so OwnDash can explain
    the difference between an up-to-date installation and a temporary network
    or GitHub failure. The automatic background path remains free to ignore
    ``ERROR`` results and stay silent.
    """
    request = _release_request(current_version)
    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ):
        return UpdateCheckResult(UpdateCheckStatus.ERROR)

    if not isinstance(payload, list):
        return UpdateCheckResult(UpdateCheckStatus.ERROR)

    release = select_newer_release(current_version, payload)
    if release is None:
        return UpdateCheckResult(UpdateCheckStatus.UP_TO_DATE)
    return UpdateCheckResult(UpdateCheckStatus.UPDATE_AVAILABLE, release)


def fetch_available_update(
    current_version: str,
    *,
    opener: Callable[..., object] = urlopen,
    timeout: float = 4.0,
) -> ReleaseInfo | None:
    """Compatibility wrapper for the original silent background-check API."""
    result = check_for_updates(
        current_version,
        opener=opener,
        timeout=timeout,
    )
    return result.release if result.status is UpdateCheckStatus.UPDATE_AVAILABLE else None
