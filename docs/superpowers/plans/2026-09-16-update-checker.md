# Background Update Checker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, optional background GitHub release check that notifies users about newer OwnDash versions without downloading or installing anything.

**Architecture:** Keep release/version/network logic in a focused core module with no widget dependencies, persist one boolean in the existing preferences JSON, and integrate the asynchronous check in `SafeShutdownWindow`. Use the standard library for HTTP and Qt's existing event loop for delayed startup and GUI-thread notification.

**Tech Stack:** Python 3.11+, PySide6, urllib.request, dataclasses, packaging/version logic implemented locally without adding dependencies, pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-update-checker.md`

## Global Constraints

- No automatic download or installation.
- GitHub Releases API is the only network source.
- Update checks default to enabled and are user-disableable.
- Network errors are silent in normal use.
- Timeout is 4 seconds.
- Stable builds ignore prereleases; prerelease builds may see prereleases and stable releases.
- Do not add a third-party networking dependency.
- Do not transmit user, profile, hardware, display, or telemetry data.

---

### Task 1: Release parsing and version comparison

**Files:**
- Create: `src/owndash/core/updates.py`
- Create: `tests/test_updates.py`

**Interfaces:**
- Produces: `ReleaseInfo(version: str, tag: str, url: str, prerelease: bool)`
- Produces: `normalize_version(value: str) -> tuple[int, int, int, int | None] | None`
- Produces: `select_newer_release(current_version: str, releases: list[object]) -> ReleaseInfo | None`

- [ ] **Step 1: Write failing tests for stable and beta normalization**

```python
from owndash.core.updates import normalize_version


def test_normalizes_internal_and_github_beta_versions():
    assert normalize_version("0.14.0b3") == (0, 14, 0, 3)
    assert normalize_version("v0.14.0-beta.3") == (0, 14, 0, 3)
    assert normalize_version("v0.14.0") == (0, 14, 0, None)
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_updates.py`
Expected: import/module failure because `owndash.core.updates` does not yet exist.

- [ ] **Step 3: Implement release normalization and selection**

Implement strict parsing for `X.Y.Z`, `X.Y.ZbN`, and GitHub tags `vX.Y.Z-beta.N`. Treat final release as newer than every beta of the same base version. Ignore malformed entries and drafts. For installed prereleases, allow prerelease candidates; for installed stable versions, ignore prerelease candidates.

- [ ] **Step 4: Add selection tests**

```python
def test_beta_can_see_newer_beta_and_final_release():
    releases = [
        {"tag_name": "v0.14.0-beta.4", "html_url": "https://example/b4", "prerelease": True, "draft": False},
        {"tag_name": "v0.14.0", "html_url": "https://example/final", "prerelease": False, "draft": False},
    ]
    result = select_newer_release("0.14.0b3", releases)
    assert result is not None
    assert result.tag == "v0.14.0"


def test_stable_ignores_prerelease():
    releases = [{"tag_name": "v0.15.0-beta.1", "html_url": "https://example/b1", "prerelease": True, "draft": False}]
    assert select_newer_release("0.14.0", releases) is None
```

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_updates.py`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/owndash/core/updates.py tests/test_updates.py
git commit -m "feat: add release version selection"
```

### Task 2: Safe GitHub release client

**Files:**
- Modify: `src/owndash/core/updates.py`
- Modify: `tests/test_updates.py`
- Modify: `src/owndash/project_info.py`

**Interfaces:**
- Produces: `GITHUB_RELEASES_API_URL`
- Produces: `fetch_available_update(current_version: str, *, opener=urlopen, timeout: float = 4.0) -> ReleaseInfo | None`

- [ ] **Step 1: Add failing network-boundary tests**

Use injected fake `opener` objects to return JSON and to raise `URLError` / `TimeoutError`. Assert only the official releases endpoint is requested, the timeout is `4.0`, malformed JSON returns `None`, and errors do not escape.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_updates.py`
Expected: missing `fetch_available_update` / URL constant.

- [ ] **Step 3: Implement the minimal client**

Use `urllib.request.Request` with `Accept: application/vnd.github+json` and `User-Agent: OwnDash/<version>`. Decode UTF-8 JSON and pass the returned list into `select_newer_release`. Catch only expected transport/decode/value failures at this boundary and return `None`.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_updates.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/owndash/core/updates.py src/owndash/project_info.py tests/test_updates.py
git commit -m "feat: fetch GitHub release updates safely"
```

### Task 3: Persist update-check preference

**Files:**
- Modify: `src/owndash/core/preferences.py`
- Create: `tests/test_update_preferences.py`

**Interfaces:**
- Produces: `AppPreferences.check_updates: bool = True`

- [ ] **Step 1: Write failing preference tests**

```python
from owndash.core.preferences import AppPreferences


def test_update_checks_default_to_enabled():
    assert AppPreferences().check_updates is True


def test_legacy_preferences_without_update_field_stay_enabled():
    prefs = AppPreferences.from_raw({"language": "de", "appearance": "dark", "setup_completed": True})
    assert prefs.check_updates is True


def test_explicit_update_opt_out_is_preserved():
    prefs = AppPreferences.from_raw({"check_updates": False})
    assert prefs.check_updates is False
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_update_preferences.py`
Expected: missing `check_updates` field.

- [ ] **Step 3: Add the preference field and parser support**

Extend the dataclass and `from_raw()` while preserving all existing language, appearance, and first-run behavior. `save_preferences()` already serializes dataclass fields via `asdict()`.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_update_preferences.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/owndash/core/preferences.py tests/test_update_preferences.py
git commit -m "feat: persist update check preference"
```

### Task 4: Expose the setting in OwnDash Settings

**Files:**
- Modify: `src/owndash/gui/main_window.py`
- Modify: `src/owndash/i18n.py`
- Create: `tests/test_update_settings_ui.py`

**Interfaces:**
- Consumes: `AppPreferences.check_updates`
- Produces: Settings checkbox wired to `self.preferences.check_updates`

- [ ] **Step 1: Write a failing structural/UI test**

Assert the Settings method creates a checkable widget initialized from `self.preferences.check_updates`, includes translated copy for automatic update checks, and persists the checkbox value before `save_preferences(self.preferences)`.

- [ ] **Step 2: Run focused test and confirm RED**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_update_settings_ui.py`
Expected: assertions fail because the checkbox does not exist.

- [ ] **Step 3: Implement the checkbox and translations**

Add one `QCheckBox` beneath the language/appearance form with concise explanatory text. On Apply, copy its state into `self.preferences.check_updates` before saving.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_update_settings_ui.py tests/test_update_preferences.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/owndash/gui/main_window.py src/owndash/i18n.py tests/test_update_settings_ui.py
git commit -m "feat: add update check setting"
```

### Task 5: Background worker and non-modal notification

**Files:**
- Modify: `src/owndash/gui/app_window.py`
- Create: `tests/test_update_window_integration.py`

**Interfaces:**
- Consumes: `fetch_available_update(__version__) -> ReleaseInfo | None`
- Produces: `SafeShutdownWindow._schedule_update_check()`
- Produces: `SafeShutdownWindow._start_update_check()`
- Produces: `SafeShutdownWindow._show_update_available(release: ReleaseInfo)`

- [ ] **Step 1: Write failing integration tests**

Tests must verify that `check_updates=False` skips scheduling, enabled checks are scheduled after startup, background work does not run on the GUI thread, and a returned release reaches the notification method. Keep real network access mocked.

- [ ] **Step 2: Run integration test and confirm RED**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_update_window_integration.py`
Expected: methods/behavior missing.

- [ ] **Step 3: Implement asynchronous check**

Use `QTimer.singleShot(1500, ...)` to defer the check. Start a daemon `Thread` for `fetch_available_update`. Deliver the result back to the GUI thread through a Qt `Signal(object)` bridge owned by the window. Never invoke widgets from the worker thread.

- [ ] **Step 4: Implement a discreet modeless update dialog**

Create a modeless notification owned by the window containing current/new version and buttons `Open release page` / `Later`. Opening the page uses the existing `webbrowser` module and the exact `ReleaseInfo.url`. Keep a reference on the window to prevent premature deletion and suppress duplicate notifications during one process lifetime.

- [ ] **Step 5: Run integration tests and confirm GREEN**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_update_window_integration.py`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/owndash/gui/app_window.py tests/test_update_window_integration.py
git commit -m "feat: notify about OwnDash updates in background"
```

### Task 6: Full regression verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `README_DE.md`
- Modify: `CHANGELOG.md`

**Interfaces:** None.

- [ ] **Step 1: Document the feature accurately**

Add a short statement that OwnDash can check GitHub for updates, that this can be disabled, and that it never downloads or installs updates automatically at this stage.

- [ ] **Step 2: Run focused update tests**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_updates.py tests/test_update_preferences.py tests/test_update_settings_ui.py tests/test_update_window_integration.py`
Expected: all pass.

- [ ] **Step 3: Run the complete suite**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m pytest -q`
Expected: zero failures.

- [ ] **Step 4: Review diff for scope and secrets**

Run: `git diff main...HEAD --check && git diff --stat main...HEAD`
Expected: no whitespace errors, only update-checker-related files plus spec/plan/docs.

- [ ] **Step 5: Commit docs**

```bash
git add README.md README_DE.md CHANGELOG.md
git commit -m "docs: document background update checks"
```

- [ ] **Step 6: Final fresh verification**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m pytest -q`
Expected: zero failures immediately before completion or merge.