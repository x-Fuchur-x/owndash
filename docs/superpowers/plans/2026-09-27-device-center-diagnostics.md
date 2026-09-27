# Device Center & Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an always-available, read-only Device Center that explains current and last-known display state, passive ArtInChip USB access, capability status, and a sanitized copyable diagnostic report without disturbing display output.

**Architecture:** Add a focused session-lifetime diagnostics service between the display lifecycle and the GUI. `SafeShutdownWindow` forwards connection/error events and supplies current display configuration; the service performs only passive probes, retains last-known state, classifies errors, and formats reports; a refactored Device Center widget renders immutable snapshots and never owns or mutates display hardware.

**Tech Stack:** Python 3.11+, PySide6, dataclasses, `enum.StrEnum`, pytest, GitHub Actions, existing PyUSB-based display backend

**Spec:** `docs/superpowers/specs/2026-09-27-device-center-diagnostics-design.md`

## Global Constraints

- Phase 1 is strictly read-only: no brightness, Expansion Screen Mode, startup-media, firmware, flash/EEPROM/XDATA, reconnect, authentication, interface claim, or other device-write operation may originate from the Device Center.
- The Device Center is visible and enabled even with no connected display.
- Current state and session-only last-known state must remain distinguishable.
- `available`, `unsupported`, and `unverified` are different semantic capability states and must not be collapsed.
- The current `33C3:0E02` optional AIC controls remain disabled; the superseded CDC/serial design must not be revived.
- Existing JPEG streaming, display switching, suspend/resume recovery, shutdown/system-state behavior, and AppImage compatibility must remain unchanged.
- Diagnostic reports must not include usernames, home-directory paths, arbitrary environment dumps, system logs, secrets, tokens, keys, or private configuration contents.
- Device-node paths such as `/dev/bus/usb/001/006` are allowed.
- Keep new diagnostic logic out of the already-large `main_window.py`; lifecycle integration stays in `gui/app_window.py`.

## Review Focus

- **Device disappears between passive probe and snapshot render:** return a coherent disconnected snapshot and preserve last-known data; never raise a modal diagnostic failure. Covered in Task 2.
- **Current udev rule cannot be inspected:** report `unknown` rather than guessing `missing` or `ok`. Covered in Task 1.
- **Error text contains `/home/<user>`, `/var/home/<user>`, or the current username:** sanitize it before storing it in a copied report. Covered in Task 3.
- **Device Center opens while a direct USB stream is active:** opening/refreshing must not call `connect()`, `close()`, `send_jpeg()`, control setters, or stop display timers. Covered in Tasks 4 and 5.
- **Backend changes after a previous AIC connection:** live snapshot must describe the selected backend while last-known AIC information stays clearly historical, not live. Covered in Tasks 2 and 5.

---

### Task 1: Passive udev diagnostic state

**Files:**
- Modify: `src/owndash/hardware/usb_setup.py`
- Modify: `tests/test_v0140_beta3_usb_setup.py`

**Interfaces:**
- Consumes: existing `RULE_NAME`, `LEGACY_RULE_NAME`, `UDEV_RULE_DIR`, `legacy_udev_rule_installed()`.
- Produces: `probe_owndash_udev_state() -> str`, returning exactly `"ok"`, `"legacy"`, `"missing"`, or `"unknown"` without invoking `pkexec`, `udevadm`, PyUSB, or device I/O.

- [ ] **Step 1: Add failing tests for current, legacy, missing, and unreadable rule state**

Add tests that monkeypatch `UDEV_RULE_DIR` to a temporary directory and assert:

```python
assert probe_owndash_udev_state() == "ok"       # 70-* exists
assert probe_owndash_udev_state() == "legacy"   # 99-* exists, even if 70-* also exists
assert probe_owndash_udev_state() == "missing"  # neither exists
assert probe_owndash_udev_state() == "unknown"  # directory inspection raises OSError
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest tests/test_v0140_beta3_usb_setup.py -q`

Expected: FAIL because `probe_owndash_udev_state` does not exist.

- [ ] **Step 3: Implement `probe_owndash_udev_state() -> str`**

Use filesystem inspection only. Give the legacy rule precedence because its presence means the known-bad late rule still requires migration. Catch `OSError` and return `"unknown"`.

- [ ] **Step 4: Run focused USB setup tests and verify GREEN**

Run: `pytest tests/test_v0140_beta3_usb_setup.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/owndash/hardware/usb_setup.py tests/test_v0140_beta3_usb_setup.py
git commit -m "feat: expose passive udev diagnostic state"
```

### Task 2: Session diagnostics model, snapshots, and lifecycle memory

**Files:**
- Create: `src/owndash/service/device_diagnostics.py`
- Create: `tests/test_device_diagnostics.py`

**Interfaces:**
- Consumes: `DisplayCapabilities`, `DisplayInfo`, `DisplayNotFoundError`, `DisplayBusyError`, `DisplayProtocolError`, `UsbAccessStatus`, `probe_artinchip_usb()`, `probe_owndash_udev_state()`.
- Produces:
  - `CapabilityStatus(StrEnum)` with `AVAILABLE`, `UNSUPPORTED`, `UNVERIFIED`.
  - `DeviceErrorCategory(StrEnum)` with `NOT_FOUND`, `PERMISSION`, `BUSY`, `PROTOCOL`, `DISCONNECTED`, `UNKNOWN`.
  - `CapabilityDiagnostic(key: str, status: CapabilityStatus)` frozen dataclass.
  - `DeviceDiagnosticSnapshot` frozen dataclass carrying the fields fixed by the spec; represent capabilities as `tuple[CapabilityDiagnostic, ...]`.
  - `DeviceDiagnosticsService.record_connected(info: DisplayInfo) -> None`.
  - `DeviceDiagnosticsService.record_disconnected() -> None`.
  - `DeviceDiagnosticsService.record_error(error: object) -> None`.
  - `DeviceDiagnosticsService.snapshot(*, backend_key: str, backend_name: str, connected: bool, current_info: DisplayInfo | None, capabilities: DisplayCapabilities, output_mode: str, rotation: int | None) -> DeviceDiagnosticSnapshot`.

- [ ] **Step 1: Add RED tests for no device, detected/inaccessible, detected/accessible, and probe failure**

Inject passive probe and clock callables into `DeviceDiagnosticsService` so tests do not touch real `/sys`. Assert AIC snapshots use `33C3:0E02`, expose device node/access when present, and degrade probe exceptions to unknown live USB state instead of raising.

- [ ] **Step 2: Run snapshot tests and verify RED**

Run: `pytest tests/test_device_diagnostics.py -q`

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement enums, frozen snapshot types, constructor injection, and passive snapshot gathering**

Constructor dependencies must permit deterministic test doubles for USB probe, udev-state probe, and clock. The service must call USB-specific probes only for `backend_key == "aic_usb"`.

- [ ] **Step 4: Add RED tests for last-known state across disconnect/reconnect and backend change**

Assert:
- `record_connected()` stores info and timestamp;
- `record_disconnected()` keeps `last_known_info` and records a later disconnect timestamp;
- a later connection replaces last-known info;
- switching the live snapshot to a non-AIC backend does not present old AIC data as current device data.

- [ ] **Step 5: Implement lifecycle memory**

Store only current-process history. Do not write diagnostics to preferences or disk.

- [ ] **Step 6: Add RED tests for capability policy and error classification**

Assert the AIC policy includes `jpeg_streaming=available`; disabled hardware brightness, device version, panel info, expansion mode, startup image/video, and hardware screen-off are `unverified`; firmware upgrade is `unsupported` unless explicitly exposed in a future backend capability. For non-AIC backends, absent optional hardware controls are `unsupported`. Assert existing display exceptions map to their stable categories and a USB-disconnect-style runtime error maps to `disconnected`.

- [ ] **Step 7: Implement capability mapping and conservative error classification**

Prefer passive probe facts over generic error text: detected plus inaccessible maps to `permission`. Do not alter the existing display exception hierarchy.

- [ ] **Step 8: Run service tests and verify GREEN**

Run: `pytest tests/test_device_diagnostics.py -q`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/owndash/service/device_diagnostics.py tests/test_device_diagnostics.py
git commit -m "feat: add read-only device diagnostics service"
```

### Task 3: Sanitized diagnostic report

**Files:**
- Modify: `src/owndash/service/device_diagnostics.py`
- Modify: `tests/test_device_diagnostics.py`

**Interfaces:**
- Consumes: `DeviceDiagnosticSnapshot` from Task 2.
- Produces:
  - `sanitize_diagnostic_text(text: str, *, home: str | None = None, username: str | None = None) -> str`.
  - `format_diagnostic_report(snapshot: DeviceDiagnosticSnapshot, *, app_version: str, system_info: dict[str, str] | None = None, home: str | None = None, username: str | None = None) -> str`.

- [ ] **Step 1: Add RED report-content tests**

Assert the report contains OwnDash version, backend, connection state, output/rotation, known display geometry/FPS, AIC VID:PID/access/device node/udev state, every capability semantic state, timestamps, and stable last-error category.

- [ ] **Step 2: Add RED sanitization tests for Linux home layouts and username leakage**

Use error messages containing `/home/alice/private.txt`, `/var/home/alice/config`, and standalone `alice`; assert none survives the returned report while `/dev/bus/usb/001/006` remains intact.

- [ ] **Step 3: Implement sanitization and deterministic plain-text report formatting**

Replace explicit supplied home/username values before report assembly. Do not dump environment variables or arbitrary mappings; only whitelist system keys intended by the spec (`distribution`, `kernel`, `desktop`, `session`) when present.

- [ ] **Step 4: Run report tests and verify GREEN**

Run: `pytest tests/test_device_diagnostics.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/owndash/service/device_diagnostics.py tests/test_device_diagnostics.py
git commit -m "feat: add sanitized device diagnostic report"
```

### Task 4: Refactor Display Controls into the read-only Device Center UI

**Files:**
- Modify: `src/owndash/gui/display_controls.py`
- Replace/expand: `tests/test_display_controls.py`

**Interfaces:**
- Consumes: `DeviceDiagnosticSnapshot`, `CapabilityStatus`.
- Produces:
  - `DeviceCenterWidget(QWidget)`.
  - `DeviceCenterWidget.__init__(snapshot: DeviceDiagnosticSnapshot, *, refresh_snapshot: Callable[[], DeviceDiagnosticSnapshot], report_text: Callable[[DeviceDiagnosticSnapshot], str], parent: QWidget | None = None, translate: Callable[[str], str] | None = None)`.
  - `DeviceCenterWidget.set_snapshot(snapshot: DeviceDiagnosticSnapshot) -> None`.

- [ ] **Step 1: Replace old hardware-control tests with RED read-only Device Center tests**

Assert the widget renders four sections (`Gerät`, `USB & Zugriff`, `Funktionen`, `Letzte Aktivität`), displays disconnected plus last-known state, visibly distinguishes all three capability states, and contains `Aktualisieren` plus `Diagnosebericht kopieren`.

- [ ] **Step 2: Run GUI tests and verify RED**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_display_controls.py -q`

Expected: FAIL because `DeviceCenterWidget` does not exist.

- [ ] **Step 3: Implement the snapshot-only Device Center presentation**

Remove the brightness slider and Expansion checkbox from phase 1. Use normal Qt labels/group boxes and the active palette; avoid hard-coded green/red as the only carrier of meaning. Assign stable object names to section/value labels and action buttons for tests.

- [ ] **Step 4: Add RED refresh and clipboard tests**

Assert clicking refresh calls only the supplied `refresh_snapshot` callback and updates the displayed snapshot. Assert copy uses `report_text(current_snapshot)` and places the result on `QApplication.clipboard()`.

- [ ] **Step 5: Implement refresh/copy behavior**

The widget must have no `DisplayBackend` reference and no hardware methods to call.

- [ ] **Step 6: Run Device Center GUI tests and verify GREEN**

Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_display_controls.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/owndash/gui/display_controls.py tests/test_display_controls.py
git commit -m "feat: turn display controls into Device Center"
```

### Task 5: Integrate Device Center with window lifecycle without disturbing streaming

**Files:**
- Modify: `src/owndash/gui/app_window.py`
- Modify: `src/owndash/i18n.py`
- Modify: `tests/test_system_state_window.py`
- Modify: `tests/test_v0120_localization_appearance.py` or add focused translation assertions to `tests/test_display_controls.py`

**Interfaces:**
- Consumes: `DeviceDiagnosticsService`, `DeviceCenterWidget`, `format_diagnostic_report()`.
- Produces:
  - always-enabled menu action text `Display & Gerät …` / `Display & Device …`;
  - `SafeShutdownWindow._device_diagnostic_snapshot() -> DeviceDiagnosticSnapshot`;
  - `SafeShutdownWindow._open_device_center() -> None`;
  - lifecycle forwarding from `_display_connected`, `_stop_display_stream`, `_display_error`, and `_quiet_reset_display_after_error`.

- [ ] **Step 1: Add RED integration test that Device Center action is enabled while disconnected**

Create `SafeShutdownWindow` with the existing offscreen fixture and assert the action is visible/enabled before any display connection.

- [ ] **Step 2: Add RED lifecycle tests for connect, disconnect, and last error**

Use `DisplayInfo("USB Bar Display", 1920, 480, 30)` and assert diagnostics receives the successful connection before transient window fields are cleared. Trigger an error then stop/reset and assert last-known info and last error remain in the resulting snapshot.

- [ ] **Step 3: Add RED non-interference test for active streaming**

Use a fake streamer/backend whose `connect`, `close`, `send_jpeg`, `set_brightness`, and `set_expansion_mode` raise immediately if called. Keep `display_timer` active, build/refresh the Device Center snapshot, and assert the timer remains active and no forbidden method ran.

- [ ] **Step 4: Implement service ownership, context gathering, lifecycle forwarding, and dialog opening**

Instantiate one `DeviceDiagnosticsService` per window. Gather backend capability data from the existing active streamer when present, otherwise use conservative defaults. Build the report system context only from the existing sensor diagnostics `system` subset and pass it through the formatter; do not collect logs.

- [ ] **Step 5: Replace connection-gated menu behavior**

Rename `display_controls_action` to a Device Center action (or retain an internal compatibility alias only if existing tests require it), keep it enabled regardless of connection, and remove the old modal message saying controls require a successful connection.

- [ ] **Step 6: Add all new German-to-English translations**

Include section titles, semantic states (`Verfügbar`, `Nicht unterstützt`, `Noch nicht verifiziert`), connection/access/udev labels, last-known wording, refresh/copy actions, and `Display & Gerät …`.

- [ ] **Step 7: Run focused integration and localization tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen pytest \
  tests/test_system_state_window.py \
  tests/test_display_controls.py \
  tests/test_v0120_localization_appearance.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/owndash/gui/app_window.py src/owndash/i18n.py tests/test_system_state_window.py tests/test_display_controls.py tests/test_v0120_localization_appearance.py
git commit -m "feat: integrate always-available Device Center"
```

### Task 6: Regression coverage, documentation, CI, and testable build

**Files:**
- Modify only if needed by verified behavior: `ROADMAP.md`, `CHANGELOG.md`
- Test: existing full suite, especially `tests/test_display_switch_shutdown.py`, `tests/test_system_state_window.py`, `tests/test_v0140_beta3_safe_shutdown.py`, `tests/test_v0140_beta3_usb_setup.py`

**Interfaces:**
- Consumes: completed Device Center implementation.
- Produces: green full CI and a Debian-12-compatible AppImage suitable for real VSDISPLAY validation.

- [ ] **Step 1: Run compile, full pytest suite, and shell syntax checks**

Run:

```bash
python -m compileall -q src
QT_QPA_PLATFORM=offscreen pytest -q
bash -n run-owndash.sh
```

Expected: all commands succeed.

- [ ] **Step 2: Fix only regressions attributable to this feature and rerun the complete suite**

Do not weaken existing streaming, suspend/resume, shutdown, USB-access, or status-screen tests to make the new feature pass.

- [ ] **Step 3: Update roadmap/changelog after behavior is proven**

Record Device Information & Diagnostics as the first implemented 0.15 Device Experience slice while explicitly keeping hardware brightness/Expansion/startup-media unverified and deferred.

- [ ] **Step 4: Commit final docs/regression adjustments**

```bash
git add ROADMAP.md CHANGELOG.md tests src
git commit -m "docs: record Device Center diagnostics slice"
```

- [ ] **Step 5: Verify GitHub Actions Tests is green on the final feature SHA**

Expected: normal repository test workflow completes successfully.

- [ ] **Step 6: Build and validate the AppImage on the existing Debian 12 baseline**

Use the repository AppImage workflow. Require the existing GLIBC compatibility gate (`<= GLIBC_2.36`) and 10-second offscreen startup smoke test to pass before handing the artifact to the user.

- [ ] **Step 7: Real-device validation on Bazzite/KDE + VSDISPLAY**

With normal dashboard streaming active:

1. open `Display & Gerät …`;
2. confirm device, `33C3:0E02`, native resolution, access and udev state;
3. click `Aktualisieren` repeatedly and verify the dashboard never pauses/flickers/reconnects;
4. copy the report and verify no username/home path appears;
5. disconnect the USB display and confirm last-known device + categorized error remain visible;
6. reconnect through the normal OwnDash flow and verify last-known data updates;
7. suspend/resume once and confirm existing bounded recovery still works;
8. perform normal Safe Shutdown/quit behavior.

Any stream interruption caused by opening or refreshing Device Center blocks completion.

- [ ] **Step 8: Final verification commit only if real-hardware findings require code/tests**

If hardware validation reveals no code change, do not create an empty commit. If a fix is needed, add a regression test first, implement it, rerun Task 6 Steps 1/5/6, and then commit the fix.
