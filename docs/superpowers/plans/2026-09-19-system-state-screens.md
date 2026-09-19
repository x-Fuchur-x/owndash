# System State Screens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reliable Linux/Bazzite system-state awareness so OwnDash can show dedicated standby, shutdown, restart, locked, and idle screens and restore the previous dashboard after resume/unlock/activity.

**Architecture:** Add a platform-neutral state model/coordinator in `core`, a mockable Linux/systemd-logind adapter in `service`, and a dedicated system-state renderer in `gui`. The main window wires state changes into the existing display output path while preserving the current application-close screen. Integration is optional and never blocks suspend, restart, or shutdown.

**Tech Stack:** Python 3.11+, PySide6 6.8+, Qt DBus (`PySide6.QtDBus`) when available, pytest, existing OwnDash display backends and i18n.

**Spec:** `docs/superpowers/specs/2026-09-19-system-state-screens-design.md`

## Global Constraints

- Beta 5 system-state integration targets Linux/Bazzite only.
- Persistent states: `ACTIVE`, `IDLE`, `LOCKED`, `SUSPENDING`, `SHUTTING_DOWN`, `RESTARTING`.
- Priority: shutdown/restart > suspend > locked > idle > active.
- Resume, unlock, and return from idle restore the prior dashboard immediately; no welcome screen.
- Missing D-Bus/systemd-logind must fall back to normal dashboard behavior.
- Suspend/restart/shutdown must never be held up indefinitely by rendering or device I/O.
- Presets: `OwnDash` and `Bazzite-inspired`; no official Bazzite logo/artwork is bundled.
- Visible state text/settings are localized in English and German.
- Quitting OwnDash while the PC remains running keeps the existing application-close screen.

## Review Focus

- Duplicate/out-of-order events must not corrupt state or overwrite the saved dashboard restoration target.
- USB disconnect during suspend/resume must recover through normal reconnect handling.
- Missing Qt DBus/logind must never prevent OwnDash startup.
- 480x1920 portrait/bar output and landscape output must both remain readable.
- Final-frame writes for shutdown/restart/suspend must be bounded and non-blocking from the OS point of view.

---

### Task 1: Normalized state model and priority resolver

**Files:**
- Create: `src/owndash/core/system_state.py`
- Create: `tests/test_system_state.py`

**Interfaces:**
- Produces: `SystemState(Enum)`, `resolve_visible_state(active_states: set[SystemState]) -> SystemState`, and `SystemStateCoordinator`.
- `SystemStateCoordinator.set_condition(state: SystemState, enabled: bool) -> SystemState | None` emits a value only when the effective visible state changes.

- [ ] **Step 1: Write failing priority/duplicate tests**

```python
from owndash.core.system_state import SystemState, SystemStateCoordinator, resolve_visible_state


def test_state_priority():
    states = {SystemState.IDLE, SystemState.LOCKED, SystemState.SUSPENDING}
    assert resolve_visible_state(states) is SystemState.SUSPENDING


def test_duplicate_condition_does_not_emit_transition():
    c = SystemStateCoordinator()
    assert c.set_condition(SystemState.LOCKED, True) is SystemState.LOCKED
    assert c.set_condition(SystemState.LOCKED, True) is None
```

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_system_state.py -v`

Expected: module/import failure.

- [ ] **Step 3: Implement enum, explicit priority map, resolver, and coordinator**

The coordinator owns the active-condition set and current visible state only; it does not render or touch hardware.

- [ ] **Step 4: Add recovery tests**

```python
def test_lock_overrides_idle_then_unlock_returns_to_idle():
    c = SystemStateCoordinator()
    c.set_condition(SystemState.IDLE, True)
    c.set_condition(SystemState.LOCKED, True)
    assert c.visible_state is SystemState.LOCKED
    assert c.set_condition(SystemState.LOCKED, False) is SystemState.IDLE


def test_clearing_suspend_returns_active():
    c = SystemStateCoordinator()
    c.set_condition(SystemState.SUSPENDING, True)
    assert c.set_condition(SystemState.SUSPENDING, False) is SystemState.ACTIVE
```

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state.py -v`

```bash
git add src/owndash/core/system_state.py tests/test_system_state.py
git commit -m "feat: add normalized system state model"
```

---

### Task 2: Mockable Linux/systemd-logind adapter

**Files:**
- Create: `src/owndash/service/system_state_linux.py`
- Create: `tests/test_system_state_linux.py`

**Interfaces:**
- Consumes: `SystemState`.
- Produces: `LinuxSystemStateAdapter(QObject)` with `condition_changed(object, bool)`, `availability_changed(bool)`, `start()`, `stop()`, and `is_available`.
- The production source uses `PySide6.QtDBus` when available; imports/connection failures are guarded.

- [ ] **Step 1: Write failing tests around an injected fake source**

Exercise semantic events for sleep preparation/resume, lock/unlock, shutdown, restart, and unavailable service without requiring a real system bus.

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_system_state_linux.py -v`

- [ ] **Step 3: Implement source abstraction + logind translation**

Translate `PrepareForSleep(true/false)` to setting/clearing `SUSPENDING`; session lock/unlock to `LOCKED`. For power-off/reboot, use the strongest available logind/systemd signal/metadata. If the platform cannot reliably distinguish reboot from power-off, do not guess: surface a neutral shutdown classification and log the limitation; the integration layer must only show `RESTARTING` when the adapter has positive reboot evidence.

- [ ] **Step 4: Add duplicate/out-of-order and missing-service tests**

Repeated identical signals must be harmless. `start()` on a system without usable Qt DBus/logind leaves `is_available == False` and raises no startup exception.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state_linux.py -v`

```bash
git add src/owndash/service/system_state_linux.py tests/test_system_state_linux.py
git commit -m "feat: add Linux system state adapter"
```

---

### Task 3: System idle detection using the session idle hint

**Files:**
- Create: `src/owndash/service/idle_state.py`
- Create: `tests/test_idle_state.py`

**Interfaces:**
- Produces: `IdleStateMonitor(QObject)` with `idle_changed(bool)`, `start()`, `stop()`, and configurable minimum idle duration.
- Production input comes from the logind session `IdleHint`/`IdleSinceHintMonotonic` properties (or an equivalent KDE/system source if logind does not expose usable values), not from OwnDash-window input events. This ensures moving the mouse or using another app exits idle correctly.
- The source is injectable for deterministic tests.

- [ ] **Step 1: Write failing tests with a fake idle source/clock**

Verify no transition before the configured duration, one `True` when system idle exceeds the threshold, and immediate `False` when the session reports active again.

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_idle_state.py -v`

- [ ] **Step 3: Implement the monitor with source polling/signal updates**

Use the system session idle hint and a small Qt timer only to evaluate duration. Keep the clock/source injectable so CI never depends on the host desktop session.

- [ ] **Step 4: Add unavailable/disabled/invalid-timeout tests**

Unavailable idle information means “do not enter OwnDash idle mode,” not a crash. Disabled idle mode emits nothing. Clamp an invalid timeout to a documented safe minimum.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_idle_state.py -v`

```bash
git add src/owndash/service/idle_state.py tests/test_idle_state.py
git commit -m "feat: add system idle monitoring"
```

---

### Task 4: Resolution-independent system-state renderer

**Files:**
- Create: `src/owndash/gui/system_state_frame.py`
- Modify: `src/owndash/gui/shutdown_frame.py`
- Create: `tests/test_system_state_frame.py`
- Modify: `tests/test_display_switch_shutdown.py`

**Interfaces:**
- Produces: `render_system_state_image(width: int, height: int, state: SystemState, theme: str, icon: QIcon, strings: dict[str, str], *, clock_text: str | None = None, date_text: str | None = None, sensor_text: str | None = None) -> QImage`.
- Existing `render_shutdown_image(...)` remains available as the application-close compatibility wrapper.

- [ ] **Step 1: Write failing portrait/landscape tests**

Verify exact image sizes for 480x1920, 1920x480, and a conventional landscape resolution; render every persistent state with both presets.

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_system_state_frame.py tests/test_display_switch_shutdown.py -v`

- [ ] **Step 3: Implement shared rendering**

Reuse the proven scaling/typography ideas from `shutdown_frame.py`. OwnDash preset uses the existing neon/HUD identity. Bazzite-inspired uses dark blue/violet styling with OwnDash-owned assets only.

- [ ] **Step 4: Add state-content/fallback tests**

Locked accepts clock/date; idle accepts minimal sensor text; suspend/shutdown/restart have distinct localized titles. Unknown theme strings fall back to OwnDash.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state_frame.py tests/test_display_switch_shutdown.py -v`

```bash
git add src/owndash/gui/system_state_frame.py src/owndash/gui/shutdown_frame.py tests/test_system_state_frame.py tests/test_display_switch_shutdown.py
git commit -m "feat: add system state screen renderer"
```

---

### Task 5: Preferences and localization

**Files:**
- Modify: `src/owndash/core/preferences.py`
- Modify: `src/owndash/i18n.py`
- Create: `tests/test_system_state_preferences.py`
- Create: `tests/test_system_state_i18n.py`

**Interfaces:**
- Extend `AppPreferences` with:
  - `system_state_screens: bool = True`
  - `system_state_theme: str = "owndash"`
  - `idle_mode: bool = True`
  - `idle_timeout_minutes: int = 30`
  - `lock_screen_state: bool = True`

- [ ] **Step 1: Write failing settings migration/validation tests**

Old Beta 4 JSON receives new defaults; `bazzite-inspired` round-trips; invalid themes fall back to `owndash`; invalid timeout values are clamped.

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_system_state_preferences.py -v`

- [ ] **Step 3: Implement preference parsing/serialization**

Keep existing settings files backwards-compatible.

- [ ] **Step 4: Add English/German keys and tests**

Cover Standby, Entering standby, System locked, Shutting down, Restarting, System state screens, Theme, OwnDash, Bazzite-inspired, Idle mode, Idle timeout, and Lock screen handling.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state_preferences.py tests/test_system_state_i18n.py -v`

```bash
git add src/owndash/core/preferences.py src/owndash/i18n.py tests/test_system_state_preferences.py tests/test_system_state_i18n.py
git commit -m "feat: add system state preferences and translations"
```

---

### Task 6: Settings UI

**Files:**
- Modify: `src/owndash/gui/main_window.py`
- Create: `tests/test_system_state_settings_ui.py`

**Interfaces:**
- Consumes the Task 5 preference fields and persists through the existing save path.

- [ ] **Step 1: Write a failing load/save GUI test**

Instantiate settings with non-default values; assert master toggle, theme selector, idle toggle, timeout, and lock toggle reflect them; edit and verify saved preference values.

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_system_state_settings_ui.py -v`

- [ ] **Step 3: Add a compact System State Screens settings group**

Theme choices are exactly OwnDash and Bazzite-inspired. Disabling the master switch disables dependent controls without erasing their values.

- [ ] **Step 4: Add dependency-state test**

Assert dependent widgets disable/re-enable correctly while preserving values.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_system_state_settings_ui.py -v`

```bash
git add src/owndash/gui/main_window.py tests/test_system_state_settings_ui.py
git commit -m "feat: add system state screen settings"
```

---

### Task 7: Integrate system states with the display lifecycle

**Files:**
- Modify: `src/owndash/gui/main_window.py`
- Modify: `src/owndash/hardware/aic_usb.py` only when the existing finite-transfer API lacks the bounded one-shot operation needed here
- Modify: `src/owndash/hardware/screen_display.py` only when standard monitor output lacks a one-frame override
- Create: `tests/test_system_state_integration.py`

**Interfaces:**
- Consumes `SystemStateCoordinator`, `LinuxSystemStateAdapter`, `IdleStateMonitor`, and `render_system_state_image()`.
- Main window owns restoration information: active dashboard/page and output destination.

- [ ] **Step 1: Write failing integration tests with fake system/display adapters**

Cover active→idle→active, active→locked→active, idle→locked priority, locked→suspend, suspend→resume restoration, positive reboot evidence→Restarting, and shutdown→Shutting down.

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/test_system_state_integration.py -v`

- [ ] **Step 3: Wire manager/adapter/idle monitor at startup**

Start only when system-state screens are enabled. Adapter failure logs and continues. Preference changes update idle/lock behavior without restarting OwnDash.

- [ ] **Step 4: Add one-shot state-frame output + restoration**

When leaving ACTIVE for the first temporary state, capture dashboard/page/destination once. Render/send on effective state changes. On return to ACTIVE, restore the captured target and immediately resume ordinary dashboard rendering.

- [ ] **Step 5: Bound critical final-frame work**

Use existing finite USB transfer timeouts; do not add retry loops that can block suspend/restart/shutdown. A failed write or disappearing display is logged and the OS transition proceeds.

- [ ] **Step 6: Add failure-path tests**

Exercise missing adapter, display write exception, USB disconnect around suspend/resume, duplicate suspend events, ambiguous shutdown metadata, and restoration after a failed final-frame write.

- [ ] **Step 7: Run integration + display regressions and commit**

Run: `pytest tests/test_system_state_integration.py tests/test_monitor_output.py tests/test_display_switch_shutdown.py tests/test_aic_usb_transfers.py -v`

```bash
git add src/owndash/gui/main_window.py src/owndash/hardware/aic_usb.py src/owndash/hardware/screen_display.py tests/test_system_state_integration.py
git commit -m "feat: integrate system state screens with display lifecycle"
```

---

### Task 8: Regression, AppImage, documentation, and Bazzite validation

**Files:**
- Modify: `README.md`
- Modify: `README_DE.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `packaging/appimage/build-appimage.sh` only if Qt DBus needs explicit bundling
- Modify: `.github/workflows/appimage.yml` only if packaging verification needs it

- [ ] **Step 1: Run the full automated suite**

Run: `pytest -q`

Expected: all existing and new tests pass.

- [ ] **Step 2: Build AppImage and verify Qt DBus inside the packaged runtime**

Use the repository’s normal AppImage build path. On Bazzite, launch the result and verify `PySide6.QtDBus` is usable. If packaging omits the needed Qt component, add only the required bundling change and rebuild.

- [ ] **Step 3: Manual Bazzite + KDE Plasma validation**

Validate both direct ArtInChip/VSDISPLAY output and standard monitor output:

1. system idle enters the minimal screen after the configured delay and any normal desktop activity restores instantly;
2. KDE lock/unlock selects Locked and restores the previous page;
3. suspend sends Standby before sleep;
4. record real hardware behavior while asleep: last frame retained, display powers off, or controller resets;
5. resume restores the previous dashboard;
6. reboot shows Restarting only when reliably detected; power-off shows Shutting down;
7. quitting OwnDash while the PC continues running still uses the existing OwnDash-closed screen;
8. no OS transition is noticeably delayed.

- [ ] **Step 4: Update documentation**

Document Linux/Bazzite support, both presets, unofficial Bazzite-inspired status/no official assets, hardware-dependent suspend-frame persistence, settings, and any reboot-detection limitation found during validation.

- [ ] **Step 5: Final regression + AppImage build**

Run: `pytest -q`, then perform one final AppImage build.

- [ ] **Step 6: Commit docs/packaging changes**

```bash
git add README.md README_DE.md ROADMAP.md CHANGELOG.md packaging/appimage/build-appimage.sh .github/workflows/appimage.yml
git commit -m "docs: document system state screens"
```

- [ ] **Step 7: Verify branch scope before PR**

```bash
git diff main...HEAD --stat
git log --oneline main..HEAD
```

Confirm the branch contains only the approved System State Screens design, plan, implementation, tests, any required packaging changes, and documentation.
