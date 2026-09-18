# Display Control & Capabilities Implementation Plan

> **Superseded plan — correction, 2026-09-18:** Checked items below are historical,
> not a statement of current hardware support. CDC transport and tty permissions
> were removed; all optional 33C3:0E02 controls remain disabled. Serial packet
> observations do not establish a USB control channel or a brightness range.
> Do not follow the hardware-control checklist below. Boot-image replacement
> needs device-specific protocol evidence before any persistent write.
> Current GUI regression tests exercise Qt offscreen rather than source text.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add capability-driven ArtInChip device information, hardware brightness, and Expansion Screen Mode control while preserving the existing authenticated JPEG streaming path.

**Architecture:** Keep image streaming on the existing PyUSB bulk transport and add the verified ArtInChip control plane as a separate CDC/serial channel owned by the same backend lifecycle. Protocol encoding/parsing stays pure in `aic_protocol.py`; Linux tty discovery and serial I/O live in `aic_cdc.py`; the GUI is capability-gated and isolated from the oversized base main-window module.

**Tech Stack:** Python 3.11+, PySide6, PyUSB, termios, pytest, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-09-17-display-control-capabilities-design.md`

## Global Constraints

- Preserve existing RSA authentication, JPEG frame transport, retry behavior, and Safe Shutdown.
- The supported control channel is 1,000,000 baud, 8N1, no flow control.
- Do not hard-code `/dev/ttyACM*` or `/dev/ttyUSB*`; discover the tty through sysfs USB ancestry.
- Do not send control `0x86`, expose generic `0x85`, or add raw flash/EEPROM/XDATA/firmware operations.
- Do not describe brightness `0%` as power-off or sleep.
- Startup JPG/MP4 remains a separate follow-up after this phase passes real-hardware verification.
- `33C3:0E02` advertises only brightness, device version, panel info, and Expansion Screen Mode in this phase.
- A missing/unavailable CDC control channel must not prevent the already-working JPEG stream from connecting.
- Explicit control actions must surface transport errors without crashing the application.

---

### Task 1: Capability model and safe backend defaults

**Files:**
- Modify: `src/owndash/core/display.py`
- Test: `tests/test_display_capabilities.py`

**Interfaces:**
- Produces: `DisplayCapabilities`, optional `DisplayInfo.device_version`, optional `DisplayInfo.expansion_mode`, and safe optional methods on `DisplayBackend`.

- [x] **Step 1: Add failing tests for conservative defaults and unsupported setters.**
- [x] **Step 2: Implement immutable `DisplayCapabilities` with all fields defaulting to `False`.**
- [x] **Step 3: Extend `DisplayInfo` without breaking existing positional callers.**
- [x] **Step 4: Add safe default getters/setters to `DisplayBackend`; unsupported setters raise `DisplayProtocolError`.**
- [x] **Step 5: Commit as `feat: add display capability model`.**

### Task 2: Pure ArtInChip control protocol

**Files:**
- Modify: `src/owndash/hardware/aic_protocol.py`
- Test: `tests/test_aic_control_protocol.py`

**Interfaces:**
- Produces:
  - `make_control_packet(command: int, payload: bytes = b"") -> bytes`
  - `brightness_to_device_value(percent: int) -> int`
  - `parse_device_version_response(data: bytes) -> str`
  - `parse_panel_info_response(data: bytes) -> tuple[int, int, bool]`

- [x] **Step 1: Add exact-byte tests for commands `0x80`, `0x81`, `0x90`, `0x91`.**
- [x] **Step 2: Add brightness boundary tests for `0,25,50,75,100` and invalid values.**
- [x] **Step 3: Add UTF-8 version and panel-info response parser tests, including malformed input.**
- [x] **Step 4: Implement `5A A5 <cmd> 00 <len:u32 LE> <payload>` packet construction.**
- [x] **Step 5: Implement `floor(percent * 255 / 100)` brightness conversion.**
- [x] **Step 6: Implement response validation and parsers without Qt/USB dependencies.**
- [x] **Step 7: Commit as `feat: add ArtInChip control protocol helpers`.**

### Task 3: Linux CDC control transport

**Files:**
- Create: `src/owndash/hardware/aic_cdc.py`
- Modify: `src/owndash/resources/99-owndash-usb.rules`
- Test: `tests/test_aic_cdc.py`

**Interfaces:**
- Produces:
  - `find_control_tty(...) -> Path | None`
  - `AicCdcControlTransport.open() / close() / write() / read_response()`

- [x] **Step 1: Discover the tty by walking `/sys/class/tty/*/device` to a USB parent matching `33c3:0e02`.**
- [x] **Step 2: Configure the tty at 1,000,000 baud, 8 data bits, no parity, one stop bit, no hardware flow control.**
- [x] **Step 3: Implement bounded write and response-read behavior with protocol-prefix/command validation.**
- [x] **Step 4: Extend udev permissions to the matching tty child interface using `ATTRS{idVendor}` / `ATTRS{idProduct}` and `TAG+="uaccess"`.**
- [x] **Step 5: Add sysfs fixture tests proving matching tty selection and unrelated-device rejection.**
- [x] **Step 6: Commit transport and permission changes.**

### Task 4: Integrate verified controls into `AicUsbDisplayBackend`

**Files:**
- Modify: `src/owndash/hardware/aic_usb.py`
- Test: `tests/test_aic_usb_controls.py`

**Interfaces:**
- Produces:
  - `get_capabilities()`
  - `get_device_version()`
  - `set_brightness(percent)`
  - `get_expansion_mode()`
  - `set_expansion_mode(enabled)`

- [x] **Step 1: Add a conservative capability constant enabling only the four verified controls.**
- [x] **Step 2: Own one `AicCdcControlTransport` instance alongside the existing USB image transport.**
- [x] **Step 3: Implement exact outgoing bytes for brightness, version query, panel query, and expansion setter.**
- [x] **Step 4: Cache returned version/state and enrich `DisplayInfo` when the control channel is available.**
- [x] **Step 5: Keep CDC enrichment non-fatal so existing authenticated JPEG streaming still connects when the control tty is absent/inaccessible.**
- [x] **Step 6: Close both transport channels in backend shutdown.**
- [x] **Step 7: Verify exact packets with an injected fake control transport.**

### Task 5: Capability-driven GUI and localization

**Files:**
- Create: `src/owndash/gui/display_controls.py`
- Modify: `src/owndash/gui/app_window.py`
- Modify: `src/owndash/i18n.py`
- Test: `tests/test_display_controls.py`

**Interfaces:**
- Produces: `DisplayControlsWidget`, plus a `Display-Steuerung …` action on `SafeShutdownWindow` that is enabled only while a compatible connected backend reports relevant capabilities.

- [x] **Step 1: Create a compact widget showing device/resolution, optional version, brightness slider, and optional Expansion Screen Mode toggle.**
- [x] **Step 2: Send brightness only when the slider is released to avoid command flooding.**
- [x] **Step 3: Catch `DisplayProtocolError` and render a non-fatal status message.**
- [x] **Step 4: Integrate the dialog in `SafeShutdownWindow` rather than expanding the already-large base `main_window.py`.**
- [x] **Step 5: Disable the action before connection and immediately on stop/error.**
- [x] **Step 6: Add English translations for all new user-facing control labels/messages.**
- [x] **Step 7: Keep CI GUI assertions headless because the minimal runner does not provide `libEGL.so.1`.**

### Task 6: Documentation, CI, and hardware gate

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: this plan and the design spec
- Pull request: `#2 Display Control & Capabilities`

- [x] **Step 1: Document capability-driven controls and explicitly avoid power-off/sleep claims.**
- [x] **Step 2: Keep Startup Image listed as the next separate hardware-verified phase rather than shipping it here.**
- [x] **Step 3: Update design/spec to describe the discovered CDC control channel and sysfs discovery.**
- [x] **Step 4: Update PR body with exact scope, exclusions, and verification status.**
- [x] **Step 5: Run GitHub CI through compileall, complete pytest suite, and shell syntax validation.**
- [ ] **Step 6: Re-run CI after the final localization/plan cleanup and record the fresh result.**
- [ ] **Step 7: Hardware-test on the real `33C3:0E02`: version/native resolution; brightness 100%, 50%, 0%, then restore; Expansion Screen Mode roundtrip; JPEG streaming; Safe Shutdown.**
- [ ] **Step 8: Only after hardware verification, mark PR ready, merge into `main`, verify `main` CI, and clean the feature branch / stale workflow artifacts where supported.**

## Hardware Verification Script

Use the normal OwnDash UI rather than sending ad-hoc serial bytes. Start the ArtInChip display stream, open **Display → Display-Steuerung …**, confirm the detected resolution/version, then test brightness at `100%`, `50%`, and `0%` and restore a comfortable brightness immediately. Toggle Expansion Screen Mode once and restore its original state. Finally verify dashboard streaming and fully quit OwnDash to confirm the Safe Shutdown frame still arrives.

Any unexpected display behavior blocks merge. Do not probe dormant `0x86`, raw flash, or firmware commands while diagnosing this phase.
