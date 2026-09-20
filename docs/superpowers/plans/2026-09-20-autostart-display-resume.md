# Autostart and Display Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let portable OwnDash start with the Linux desktop session and automatically reconnect its USB display on launch when the user opts in.

**Architecture:** Add a small XDG autostart service that writes/removes `~/.config/autostart/owndash.desktop` and uses the current AppImage path when available. Add two persisted preferences (`launch_at_login`, `start_display_on_launch`) and expose them in Settings. On application startup, schedule a non-blocking display start only when the preference is enabled and first-run setup is complete.

**Tech Stack:** Python 3.12, PySide6, XDG desktop autostart, pytest.

**Spec:** User request in conversation: portable AppImage should be able to start automatically after Bazzite login and reconnect the VSDISPLAY without having to remember “Display starten”.

## Global Constraints

- Keep `main` untouched; implement on `feat/autostart-display-resume` based on `fix/system-state-dbus-pyside`.
- No background daemon or installer is required.
- Autostart must be opt-in and removable from OwnDash settings.
- Auto display start must be opt-in, non-blocking, and must not run during first-run setup.
- Preserve current system-state behavior: never invent a reboot/shutdown classification without positive evidence.

## Review Focus

- AppImage paths containing spaces must produce a valid desktop `Exec=` line.
- Disabling autostart must remove the XDG entry without failing when it is already absent.
- Existing settings files must migrate with both new booleans defaulting safely.
- Auto display start must not double-start an already running streamer.
- First-run setup must remain in control; auto display connection must not race it.

---

### Task 1: XDG autostart service

**Files:**
- Create: `src/owndash/service/autostart.py`
- Create: `tests/test_autostart.py`

**Interfaces:**
- Produces: `autostart_path() -> Path`, `set_autostart_enabled(enabled: bool) -> None`, `render_autostart_entry(command: list[str]) -> str`.

- [ ] Write failing tests for XDG path resolution, AppImage launch command quoting, entry creation, and idempotent removal.
- [ ] Run the new tests and verify RED because the module does not exist.
- [ ] Implement the minimal service with atomic UTF-8 file writes and no shell invocation.
- [ ] Run the new tests and verify GREEN.

### Task 2: Persist preferences and settings UI

**Files:**
- Modify: `src/owndash/core/preferences.py`
- Modify: `src/owndash/gui/app_window.py`
- Modify: `src/owndash/i18n.py`
- Modify/Create preference tests as appropriate.

**Interfaces:**
- Produces: `AppPreferences.launch_at_login: bool` and `AppPreferences.start_display_on_launch: bool`.
- Consumes: `set_autostart_enabled()` from Task 1.

- [ ] Write failing migration tests proving old settings default both flags to `False` and new raw values round-trip.
- [ ] Verify RED.
- [ ] Add the two dataclass fields/from_raw mappings.
- [ ] Add two Settings checkboxes and localized copy; applying Settings updates the XDG entry and persists both flags.
- [ ] Verify targeted tests GREEN.

### Task 3: Automatic display reconnect on application launch

**Files:**
- Modify: `src/owndash/gui/app_window.py`
- Create/Modify: startup behavior tests.

**Interfaces:**
- Consumes: `AppPreferences.start_display_on_launch`.
- Produces: `_auto_start_display_if_enabled()` startup hook.

- [ ] Write a failing test for the pure decision helper: start only when preference is enabled, setup is complete, and no streamer is already running.
- [ ] Verify RED.
- [ ] Implement the helper and schedule it with `QTimer.singleShot` after window initialization.
- [ ] Keep standard-monitor output conservative: automatic startup is allowed only for `aic_usb`; screen output still requires the existing confirmation dialog.
- [ ] Verify targeted tests GREEN.

### Task 4: Full verification and hardware AppImage

**Files:**
- Temporary CI trigger only; restore it before completion.

- [ ] Run `python -m compileall -q src tests`.
- [ ] Run full `pytest -q` and require all tests green.
- [ ] Run `bash -n run-owndash.sh`.
- [ ] Build AppImage on Debian 12, verify GLIBC <= 2.36 and 10-second offscreen smoke test.
- [ ] Restore normal AppImage workflow triggers and rerun normal test CI.
- [ ] Keep `main` unchanged and provide the hardware-test AppImage.