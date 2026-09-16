# OwnDash Background Update Checker Specification

## Goal

Add a safe, low-noise background update check to OwnDash. The first stage only detects newer GitHub releases and informs the user; it never downloads or installs software automatically.

## User experience

- Update checks are enabled by default and can be disabled in Settings.
- The check starts shortly after the main window is ready so startup is not blocked.
- Network failures, GitHub outages, malformed responses, or timeouts are silent in normal use.
- If no newer release exists, nothing is shown.
- If a newer release exists, OwnDash shows a discreet in-app notification containing the installed version and available version plus an action to open the GitHub release page.
- No automatic download, no automatic replacement of the AppImage, no privilege escalation, and no background installer.
- The notification must not interrupt an active USB display stream.

## Release policy

- Release metadata comes from the official repository `x-Fuchur-x/owndash` via the public GitHub Releases API.
- Stable builds only consider stable releases.
- Beta/prerelease builds may consider newer prereleases as well as newer stable releases.
- Draft releases are ignored.
- Version comparison uses PEP 440-compatible normalized versions so `0.14.0b3 < 0.14.0b4 < 0.14.0 < 0.15.0`.
- GitHub tag names such as `v0.14.0-beta.3` must normalize to the same semantic version as OwnDash's internal `0.14.0b3`.

## Architecture

Create a focused `owndash.core.updates` module containing release parsing, version normalization/comparison, and a small network client. The core layer must be testable without Qt widgets and without real network access.

The GUI integration lives in `SafeShutdownWindow` so the already-small lifecycle subclass remains the integration point for post-start background behavior. It schedules the check with `QTimer.singleShot`, runs network I/O in a worker thread, and forwards completion to the GUI thread before touching widgets.

Preferences gain a single boolean `check_updates`, defaulting to `True`. The existing Settings dialog exposes this as `Automatically check for updates` / German equivalent and persists it through the existing JSON preferences mechanism.

The first-stage notification should reuse existing Qt primitives rather than introduce a new dependency: a non-modal `QMessageBox` or equivalent small modeless dialog with `Open release page` and `Later`. It must never block startup or display streaming.

## Networking and privacy

- Use Python's standard library (`urllib.request`) to avoid adding a dependency.
- Request only the official GitHub Releases API endpoint.
- Send a short OwnDash User-Agent and request JSON.
- Use a finite timeout of 4 seconds.
- Do not transmit profile contents, hardware data, display identifiers, or settings.
- No telemetry and no persistent tracking identifier.

## Failure behavior

All expected network and parse failures return `None` / no update and are silent. Programming errors remain test-visible and should not be broadly swallowed outside the narrow network boundary.

## Testing

Automated tests must cover:

- preference default, persistence, and invalid legacy data compatibility;
- tag normalization for stable and beta tags;
- equal, older, newer beta, beta-to-stable, and stable-to-prerelease comparisons;
- draft filtering;
- stable channel excluding prereleases;
- beta channel accepting appropriate prereleases;
- malformed API objects;
- timeout / URL error behavior;
- GUI wiring: disabled preference means no check, enabled preference schedules one, and an available release produces the notification path without blocking.

## Out of scope

- downloading AppImages;
- self-replacement of the running AppImage;
- restart-to-update;
- signatures beyond HTTPS/GitHub transport;
- delta updates;
- update channels beyond stable/prerelease inference from the installed version.

Those belong to the later integrated AppImage updater stage.