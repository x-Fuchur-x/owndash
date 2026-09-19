# System State Screens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reliable Linux/Bazzite system-state awareness so OwnDash can show dedicated standby, shutdown, restart, locked, and idle screens and restore the previous dashboard after resume/unlock/activity.

**Architecture:** Introduce a platform-neutral state model and coordinator in `core`, a Linux/systemd-logind adapter in `service`, and a dedicated state-screen renderer in `gui`. The main window wires these pieces into the existing display-output path while preserving the existing application-close screen. System integration remains optional and must never block suspend, restart, or shutdown.

**Tech Stack:** Python 3.11+, PySide6 6.8+, Qt DBus (`PySide6.QtDBus`) where available, pytest, existing OwnDash display backends and i18n system.

**Spec:** `docs/superpowers/specs/2026-09-19-system-state-screens-design.md`

## Global Constraints

- Linux/Bazzite support only for Beta 5; Windows/macOS system-state integration stays out of scope.
- Supported persistent states: `ACTIVE`, `IDLE`, `LOCKED`, `SUSPENDING`, `SHUTTING_DOWN`, `RESTARTING`.
- Priority: shutdown/restart > suspend > locked > idle > active.
- Resume, unlock, and activity return restore the previous dashboard immediately; no welcome screen.
- System-state integration must be optional and fail open to normal dashboard operation.
- Suspend/restart/shutdown must never be delayed indefinitely by rendering or device I/O.
- Provide two presets: `OwnDash` and `Bazzite-inspired`; do not bundle official Bazzite logo/artwork.
- All visible state text and settings labels use the existing English/German localization system.
- Preserve the current application-close screen for quitting OwnDash while the computer remains running.

## Review Focus

- Duplicate/out-of-order system events must not corrupt the active state or overwrite the saved dashboard restoration target.
- A USB display that disconnects during suspend/resume must recover through normal reconnect logic without crashing.
- Missing Qt DBus/systemd-logind must leave OwnDash fully usable and must not produce a startup failure.
- Portrait bar displays (notably 480x1920) and landscape displays must both render readable state screens.
- Shutdown/restart event handling must be bounded in time so slow or failed display writes never stall the OS transition.

---

### Task 1: Add the normalized state model and priority resolver

**Files:**
- Create: `src/owndash/core/system_state.py`
- Create: `tests/test_system_state.py`

**Interfaces:**
- Produces: `SystemState(Enum)`, `SystemStateSnapshot`, `resolve_visible_state(active_states: set[SystemState]) -> SystemState`, `SystemStateCoordinator`.
- `SystemStateCoordinator.set_condition(state: SystemState, enabled: bool) -> SystemState | None` returns a newly visible state only when visibility changes.
- `SystemStateCoordinator.restore_target` stores an opaque runtime token supplied by the GUI only while a temporary state is active.

- [ ] **Step 1: Write failing tests for priority and duplicate-event behavior**

```python
from owndash.core.system_state import SystemState, SystemStateCoordinator, resolve_visible_state


def test_state_priority():
    states = {SystemState.IDLE, SystemState.LOCKED, SystemState.SUSPENDING}
    assert resolve_visible_state(states) is SystemState.SUSPENDING


def test_duplicate_condition_does_not_emit_transition():
    coordinator = SystemStateCoordinator()
    assert coordinator.set_condition(SystemState.LOCKED, True) is SystemState.LOCKED
    assert coordinator.set_condition(SystemState.LOCKED, True) is None
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `pytest tests/test_system_state.py -v`

Expected: import/module failure because `owndash.core.system_state` does not exist.

- [ ] **Step 3: Implement the minimal normalized model**

Create an enum with exactly `ACTIVE`, `IDLE`, `LOCKED`, `SUSPENDING`, `SHUTTING_DOWN`, `RESTARTING`, an explicit priority map, a resolver, and a coordinator that keeps a condition set and emits only effective visible-state changes.

- [ ] **Step 4: Add tests for recovery transitions**

```python
def test_lock_overrides_idle_then_unlock_returns_to_idle():
    c = SystemStateCoordinator()
    c.set_condition(SystemState.IDLE, True)
    c.set_condition(SystemState.LOCKED, True)
    assert c.visible_state is SystemState.LOCKED
    assert c.set_condition(SystemState.LOCKED, False) is SystemState.IDLE


def test_clearing_last_temporary_state_returns_active():
    c = SystemStateCoordinator()
    c.set_condition(SystemState.SUSPENDING, True)
    assert c.set_condition(SystemState.SUSPENDING, False) is SystemState.ACTIVE
```

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state.py -v`

Expected: PASS.

```bash
git add src/owndash/core/system_state.py tests/test_system_state.py
git commit -m "feat: add normalized system state model"
```

---

### Task 2: Add a mockable Linux system-state adapter

**Files:**
- Create: `src/owndash/service/system_state_linux.py`
- Create: `tests/test_system_state_linux.py`

**Interfaces:**
- Consumes: `SystemState` from Task 1.
- Produces: `LinuxSystemStateAdapter(QObject)` with Qt signals `condition_changed(object, bool)` and `availability_changed(bool)` plus `start()`, `stop()`, and `is_available`.
- Linux adapter listens to systemd-logind manager/session signals through `PySide6.QtDBus` when present; imports must be guarded so OwnDash starts even when Qt DBus support is unavailable.

- [ ] **Step 1: Write failing tests around a fake signal source**

Test the adapter’s translation layer independently from a real system bus. Inject a tiny fake source that emits semantic events such as `prepare_for_sleep(True)`, `locked(True)`, and shutdown/restart preparation.

- [ ] **Step 2: Verify focused tests fail**

Run: `pytest tests/test_system_state_linux.py -v`

Expected: module/import failure.

- [ ] **Step 3: Implement the adapter with a narrow source abstraction**

Keep D-Bus connection code separate from event normalization. Translate sleep preparation to `SUSPENDING`; resume clears it. Translate session lock/unlock to `LOCKED`. Keep shutdown and restart as separate conditions when the source can distinguish them; if the platform cannot distinguish a power-off preparation from restart reliably, expose a small injectable classifier and log the ambiguity rather than guessing silently.

- [ ] **Step 4: Add missing-service and duplicate-signal tests**

Test that `start()` leaves `is_available == False` instead of raising when the system bus/logind cannot be reached, and that repeated identical source signals produce no malformed state sequence.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state_linux.py -v`

Expected: PASS.

```bash
git add src/owndash/service/system_state_linux.py tests/test_system_state_linux.py
git commit -m "feat: add Linux system state adapter"
```

---

### Task 3: Add idle detection without coupling it to logind

**Files:**
- Create: `src/owndash/service/idle_state.py`
- Create: `tests/test_idle_state.py`

**Interfaces:**
- Produces: `IdleStateMonitor(QObject)` with `idle_changed(bool)` and configurable timeout in seconds.
- Idle monitoring uses Qt/application activity timestamps and is independent from lock/suspend detection, so it remains testable without D-Bus.

- [ ] **Step 1: Write tests with an injected monotonic clock**

Verify activity resets the deadline, no idle transition occurs before the timeout, one transition occurs after timeout, and the next activity emits `False` immediately.

- [ ] **Step 2: Run failing tests**

Run: `pytest tests/test_idle_state.py -v`

- [ ] **Step 3: Implement the timer/clock-based monitor**

Use an injectable clock and explicit `record_activity()`/`check()` methods for deterministic tests; wire a `QTimer` only as the production scheduler.

- [ ] **Step 4: Add disabled/zero-timeout tests**

Ensure disabled idle handling never emits idle and invalid timeout values are clamped to a documented minimum rather than creating a busy loop.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_idle_state.py -v`

```bash
git add src/owndash/service/idle_state.py tests/test_idle_state.py
git commit -m "feat: add idle state monitoring"
```

---

### Task 4: Generalize the shutdown artwork into a system-state renderer

**Files:**
- Create: `src/owndash/gui/system_state_frame.py`
- Modify: `src/owndash/gui/shutdown_frame.py`
- Create: `tests/test_system_state_frame.py`
- Modify: `tests/test_display_switch_shutdown.py`

**Interfaces:**
- Consumes: `SystemState`.
- Produces: `render_system_state_image(width: int, height: int, state: SystemState, theme: str, icon: QIcon, strings: dict[str, str], *, clock_text: str | None = None, date_text: str | None = None, sensor_text: str | None = None) -> QImage`.
- `render_shutdown_image(...)` remains available as a compatibility wrapper for the existing application-close behavior.

- [ ] **Step 1: Write failing portrait/landscape rendering tests**

Verify exact output dimensions for 480x1920, 1920x480, and a conventional landscape size, plus non-null images for every persistent state and both theme names.

- [ ] **Step 2: Run failing renderer tests**

Run: `pytest tests/test_system_state_frame.py tests/test_display_switch_shutdown.py -v`

- [ ] **Step 3: Implement shared resolution-independent rendering**

Reuse the proven scaling/typography ideas from `shutdown_frame.py`, but make content state-driven. `OwnDash` keeps the neon/HUD identity. `Bazzite-inspired` uses dark blue/violet styling and only OwnDash-owned assets.

- [ ] **Step 4: Add state-specific content tests**

Check that locked frames accept clock/date, idle accepts minimal sensor text, suspend/shutdown/restart use distinct localized titles, and unsupported theme values fall back to `OwnDash` instead of crashing.

- [ ] **Step 5: Preserve the existing application-close wrapper and commit**

Run: `pytest tests/test_system_state_frame.py tests/test_display_switch_shutdown.py -v`

```bash
git add src/owndash/gui/system_state_frame.py src/owndash/gui/shutdown_frame.py tests/test_system_state_frame.py tests/test_display_switch_shutdown.py
git commit -m "feat: add system state screen renderer"
```

---

### Task 5: Persist system-state preferences and add localized strings

**Files:**
- Modify: `src/owndash/core/preferences.py`
- Modify: `src/owndash/i18n.py`
- Create: `tests/test_system_state_preferences.py`
- Modify: existing i18n tests if present; otherwise add `tests/test_system_state_i18n.py`

**Interfaces:**
- Extend `AppPreferences` with:
  - `system_state_screens: bool = True`
  - `system_state_theme: str = "owndash"`
  - `idle_mode: bool = True`
  - `idle_timeout_minutes: int = 30`
  - `lock_screen_state: bool = True`

- [ ] **Step 1: Write preference migration tests**

Verify old settings JSON without the new keys loads the new defaults, valid `bazzite-inspired` persists, invalid theme falls back to `owndash`, and unreasonable timeout values are clamped to a safe range.

- [ ] **Step 2: Run failing preference tests**

Run: `pytest tests/test_system_state_preferences.py -v`

- [ ] **Step 3: Extend `AppPreferences.from_raw()` and serialization**

Keep backwards compatibility with Beta 4 settings files.

- [ ] **Step 4: Add English/German strings**

At minimum add localized keys for Standby, Entering standby, System locked, Shutting down, Restarting, System state screens, Theme, OwnDash, Bazzite-inspired, Idle mode, Idle timeout, and Lock screen handling.

- [ ] **Step 5: Run preference/i18n tests and commit**

Run: `pytest tests/test_system_state_preferences.py tests/test_system_state_i18n.py -v`

```bash
git add src/owndash/core/preferences.py src/owndash/i18n.py tests/test_system_state_preferences.py tests/test_system_state_i18n.py
git commit -m "feat: add system state preferences and translations"
```

---

### Task 6: Add settings UI controls

**Files:**
- Modify: `src/owndash/gui/main_window.py`
- Create: `tests/test_system_state_settings_ui.py`

**Interfaces:**
- Consumes the new `AppPreferences` fields from Task 5.
- Produces UI controls that persist through the existing preferences save path.

- [ ] **Step 1: Write a failing GUI test for loading/saving controls**

Instantiate the settings UI with non-default preferences and verify the enabled toggle, theme selector, idle toggle, timeout value, and lock-screen toggle reflect stored values; then change them and verify the saved `AppPreferences` values.

- [ ] **Step 2: Run the focused GUI test**

Run: `pytest tests/test_system_state_settings_ui.py -v`

- [ ] **Step 3: Add a compact System State Screens settings section**

Follow the existing settings layout conventions. Disable subordinate idle/lock controls when system-state screens are globally disabled. Theme choices must be exactly OwnDash and Bazzite-inspired.

- [ ] **Step 4: Add dependency-state tests**

Verify disabling the master toggle disables dependent controls without destroying their stored values.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state_settings_ui.py -v`

```bash
git add src/owndash/gui/main_window.py tests/test_system_state_settings_ui.py
git commit -m "feat: add system state screen settings"
```

---

### Task 7: Wire state transitions into the existing display lifecycle

**Files:**
- Modify: `src/owndash/gui/main_window.py`
- Modify: `src/owndash/hardware/aic_usb.py` only if a bounded final-frame timeout/cancel hook is required by the existing API
- Modify: `src/owndash/hardware/screen_display.py` only if standard monitor output needs an explicit one-frame override
- Create: `tests/test_system_state_integration.py`

**Interfaces:**
- Consumes: `SystemStateCoordinator`, `LinuxSystemStateAdapter`, `IdleStateMonitor`, `render_system_state_image()`.
- Main window owns runtime restoration data: active dashboard/page plus current output destination.
- A temporary state frame is written through the same backend-selection logic as normal frames.

- [ ] **Step 1: Write failing integration tests with fake adapter/backends**

Cover active -> idle -> active, active -> locked -> active, idle -> locked priority, locked -> suspend, suspend -> resume restoration, and shutdown vs restart frame selection.

- [ ] **Step 2: Run failing integration tests**

Run: `pytest tests/test_system_state_integration.py -v`

- [ ] **Step 3: Wire the coordinator and adapter at application startup**

Only start Linux integration when system-state screens are enabled. A failed adapter start must log and continue. Hook idle monitoring to user activity and preference changes.

- [ ] **Step 4: Add one-shot temporary-frame output and restoration**

Before entering the first non-active visible state, capture the current dashboard/page and display target exactly once. Render/send state frames on visibility changes. When visible state returns to `ACTIVE`, restore the captured target and resume normal dashboard updates immediately.

- [ ] **Step 5: Bound suspend/shutdown/restart display work**

Ensure the last-frame attempt uses the backend’s existing finite USB timeouts. Do not add blocking retry loops. If a write fails or the device disappears, record/log the failure and let the OS transition continue.

- [ ] **Step 6: Add failure-path tests**

Test missing adapter availability, display write exception, USB disconnect around suspend/resume, duplicate suspend signals, and restoration after a failed final-frame write.

- [ ] **Step 7: Run integration + existing display tests and commit**

Run: `pytest tests/test_system_state_integration.py tests/test_monitor_output.py tests/test_display_switch_shutdown.py tests/test_aic_usb_transfers.py -v`

```bash
git add src/owndash/gui/main_window.py src/owndash/hardware/aic_usb.py src/owndash/hardware/screen_display.py tests/test_system_state_integration.py
git commit -m "feat: integrate system state screens with display lifecycle"
```

---

### Task 8: Full regression, packaging check, documentation, and Bazzite manual validation

**Files:**
- Modify: `README.md`
- Modify: `README_DE.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `packaging/appimage/build-appimage.sh` only if Qt DBus libraries/plugins need explicit bundling
- Modify: `.github/workflows/appimage.yml` only if packaging verification requires it

**Interfaces:**
- No new runtime interface; this task proves and documents the completed feature.

- [ ] **Step 1: Run the complete automated suite**

Run: `pytest -q`

Expected: all tests pass, with the existing Beta 4 suite plus the new system-state tests.

- [ ] **Step 2: Build the AppImage and inspect Qt DBus availability**

Run the repository’s documented AppImage build path. Launch the AppImage on Bazzite and confirm `PySide6.QtDBus` loads inside the packaged runtime. If it does not, update only the AppImage bundling inputs needed to include the Qt DBus component and rebuild.

- [ ] **Step 3: Manually validate on Bazzite + KDE Plasma**

Check both direct ArtInChip/VSDISPLAY USB output and standard monitor output:

1. idle timeout enters the minimal screen and activity restores instantly;
2. KDE lock shows the locked screen and unlock restores the previous page;
3. suspend sends Standby before sleep;
4. record whether the physical 8.8-inch display retains the frame, powers off, or resets while asleep;
5. resume restores the previous dashboard;
6. restart shows Restarting and shutdown shows Shutting down;
7. quitting OwnDash while the PC remains running still shows the existing OwnDash-closed screen;
8. no OS transition is noticeably delayed by OwnDash.

- [ ] **Step 4: Update documentation**

Document Linux/Bazzite support, the two visual presets, the fact that Bazzite-inspired is unofficial and uses no official Bazzite assets, hardware-dependent suspend-frame persistence, and the settings users can change.

- [ ] **Step 5: Run a final regression and commit**

Run: `pytest -q`

Then run the AppImage build one final time.

```bash
git add README.md README_DE.md ROADMAP.md CHANGELOG.md packaging/appimage/build-appimage.sh .github/workflows/appimage.yml
git commit -m "docs: document system state screens"
```

- [ ] **Step 6: Verify branch scope before PR**

Run:

```bash
git diff main...HEAD --stat
git log --oneline main..HEAD
```

Confirm the branch contains only the approved System State Screens design, plan, implementation, tests, packaging adjustments if required, and documentation.
