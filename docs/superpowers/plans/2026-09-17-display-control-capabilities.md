# Display Control & Capabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add capability-driven ArtInChip display information, hardware brightness, and Expansion Screen Mode control without disturbing the existing JPEG streaming path.

**Architecture:** Extend the core display contract with conservative optional capabilities, keep ArtInChip packet encoding/decoding pure in `aic_protocol.py`, and let `AicUsbDisplayBackend` expose only verified controls. Add a small Qt control surface that appears only for capabilities reported by the connected backend.

**Tech Stack:** Python 3.11+, PySide6, PyUSB, pytest

**Spec:** `docs/superpowers/specs/2026-09-17-display-control-capabilities-design.md`

## Global Constraints

- Preserve the existing direct JPEG/authentication transport and Safe Shutdown behavior.
- Do not send unknown command `0x86` or expose `0x85` as a user control.
- Do not implement raw flash, EEPROM, XDATA, firmware upgrade, or claim brightness 0% is power-off.
- `33C3:0E02` enables only verified capabilities in this phase: brightness, device version, panel info, Expansion Screen Mode.
- All protocol byte construction/parsing must be unit-testable without physical hardware.
- Existing screen display backends must remain compatible.

---

### Task 1: Capability model and safe backend defaults

**Files:**
- Modify: `src/owndash/core/display.py`
- Test: `tests/test_display_capabilities.py`

**Interfaces:**
- Produces: `DisplayCapabilities`, extended `DisplayInfo`, and default optional control methods on `DisplayBackend`.
- Consumes: existing `DisplayProtocolError`.

- [ ] **Step 1: Write failing capability/default tests**

```python
from owndash.core.display import DisplayBackend, DisplayCapabilities, DisplayInfo, DisplayProtocolError


class DummyBackend(DisplayBackend):
    def connect(self) -> DisplayInfo:
        return DisplayInfo("dummy", 100, 200)

    def send_jpeg(self, payload: bytes) -> None:
        pass

    def close(self) -> None:
        pass


def test_capabilities_default_to_safe_false_values():
    caps = DisplayCapabilities()
    assert caps.hardware_brightness is False
    assert caps.device_version is False
    assert caps.panel_info is False
    assert caps.expansion_mode is False
    assert caps.startup_image is False
    assert caps.startup_video is False
    assert caps.hardware_screen_off is False
    assert caps.firmware_upgrade is False


def test_optional_controls_fail_safely_by_default():
    backend = DummyBackend()
    assert backend.get_capabilities() == DisplayCapabilities()
    assert backend.get_device_version() is None
    assert backend.get_expansion_mode() is None
    try:
        backend.set_brightness(50)
    except DisplayProtocolError:
        pass
    else:
        raise AssertionError("unsupported brightness must raise DisplayProtocolError")
```

- [ ] **Step 2: Run the new test and verify it fails**

Run: `PYTHONPATH=src pytest -q tests/test_display_capabilities.py`

Expected: FAIL because `DisplayCapabilities` and optional methods do not exist yet.

- [ ] **Step 3: Implement the core model**

Add to `src/owndash/core/display.py`:

```python
@dataclass(frozen=True, slots=True)
class DisplayCapabilities:
    hardware_brightness: bool = False
    device_version: bool = False
    panel_info: bool = False
    expansion_mode: bool = False
    startup_image: bool = False
    startup_video: bool = False
    hardware_screen_off: bool = False
    firmware_upgrade: bool = False
```

Extend `DisplayInfo` with optional metadata while preserving existing positional call sites:

```python
@dataclass(frozen=True, slots=True)
class DisplayInfo:
    name: str
    width: int
    height: int
    refresh_hz: int | None = None
    device_version: str | None = None
    expansion_mode: bool | None = None
```

Add concrete safe defaults to `DisplayBackend`:

```python
def get_capabilities(self) -> DisplayCapabilities:
    return DisplayCapabilities()

def get_device_version(self) -> str | None:
    return None

def set_brightness(self, percent: int) -> None:
    raise DisplayProtocolError("Hardware-Helligkeit wird von diesem Display nicht unterstützt.")

def get_expansion_mode(self) -> bool | None:
    return None

def set_expansion_mode(self, enabled: bool) -> None:
    raise DisplayProtocolError("Expansion Screen Mode wird von diesem Display nicht unterstützt.")
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=src pytest -q tests/test_display_capabilities.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/owndash/core/display.py tests/test_display_capabilities.py
git commit -m "feat: add display capability model"
```

### Task 2: Pure ArtInChip control protocol helpers

**Files:**
- Modify: `src/owndash/hardware/aic_protocol.py`
- Test: `tests/test_aic_control_protocol.py`

**Interfaces:**
- Produces: `make_control_packet(command: int, payload: bytes = b"") -> bytes`, `brightness_to_device_value(percent: int) -> int`, `parse_device_version_response(data: bytes) -> str`, and `parse_panel_info_response(data: bytes) -> tuple[int, int, bool]`.
- Consumes: no USB or Qt objects.

- [ ] **Step 1: Write exact packet and parser tests**

```python
import pytest
from owndash.hardware.aic_protocol import (
    brightness_to_device_value,
    make_control_packet,
    parse_device_version_response,
    parse_panel_info_response,
)


def test_control_packet_layout():
    assert make_control_packet(0x80, b"\x7f") == bytes.fromhex("5a a5 80 00 01 00 00 00 7f")
    assert make_control_packet(0x81, b"\x01") == bytes.fromhex("5a a5 81 00 01 00 00 00 01")
    assert make_control_packet(0x90, b"\x01") == bytes.fromhex("5a a5 90 00 01 00 00 00 01")
    assert make_control_packet(0x91, b"\x01") == bytes.fromhex("5a a5 91 00 01 00 00 00 01")


@pytest.mark.parametrize("percent,expected", [(0, 0), (25, 63), (50, 127), (75, 191), (100, 255)])
def test_brightness_mapping(percent, expected):
    assert brightness_to_device_value(percent) == expected


def test_brightness_rejects_out_of_range():
    with pytest.raises(ValueError):
        brightness_to_device_value(-1)
    with pytest.raises(ValueError):
        brightness_to_device_value(101)


def test_parse_device_version_utf8_payload():
    packet = b"\x5a\xa5\x00\x81\x00" + "1.2.3".encode("utf-8")
    assert parse_device_version_response(packet) == "1.2.3"


def test_parse_panel_info_response():
    packet = bytes([0x5A, 0xA5, 0x00, 0x90, 0, 0, 0, 0, 0x01, 0xE0, 0x07, 0x80, 0x01])
    assert parse_panel_info_response(packet) == (480, 1920, True)
```

Also add short/malformed-response rejection tests.

- [ ] **Step 2: Verify failure**

Run: `PYTHONPATH=src pytest -q tests/test_aic_control_protocol.py`

Expected: FAIL because helpers are not implemented.

- [ ] **Step 3: Implement protocol helpers**

Use a single control-header helper:

```python
CONTROL_PREFIX = b"\x5a\xa5"


def make_control_packet(command: int, payload: bytes = b"") -> bytes:
    if not 0 <= command <= 0xFF:
        raise ValueError("command out of range")
    return CONTROL_PREFIX + bytes((command, 0)) + struct.pack("<I", len(payload)) + payload


def brightness_to_device_value(percent: int) -> int:
    if not 0 <= percent <= 100:
        raise ValueError("brightness percent out of range")
    return (percent * 255) // 100
```

Parsers must validate minimum length and response command before decoding fields. `parse_panel_info_response` reads width from bytes 8-9 and height from bytes 10-11 as big-endian and returns `bool(data[12])`.

- [ ] **Step 4: Run protocol tests**

Run: `PYTHONPATH=src pytest -q tests/test_aic_control_protocol.py`

Expected: PASS.

- [ ] **Step 5: Run existing protocol tests**

Run: `PYTHONPATH=src pytest -q tests/test_protocol.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/owndash/hardware/aic_protocol.py tests/test_aic_control_protocol.py
git commit -m "feat: add ArtInChip control protocol helpers"
```

### Task 3: ArtInChip backend controls

**Files:**
- Modify: `src/owndash/hardware/aic_usb.py`
- Test: `tests/test_aic_usb_controls.py`

**Interfaces:**
- Consumes: `DisplayCapabilities`, `make_control_packet`, `brightness_to_device_value`, response parsers.
- Produces: `AicUsbDisplayBackend.get_capabilities`, `.get_device_version`, `.set_brightness`, `.get_expansion_mode`, `.set_expansion_mode`.

- [ ] **Step 1: Write fake-transport tests for capabilities and outgoing bytes**

Create an `AicUsbDisplayBackend` instance and inject a fake `_dev` with deterministic `write/read` calls. Tests must assert:

```python
assert backend.get_capabilities().hardware_brightness is True
assert backend.get_capabilities().device_version is True
assert backend.get_capabilities().panel_info is True
assert backend.get_capabilities().expansion_mode is True
assert backend.get_capabilities().startup_image is False
```

For brightness 50%, assert exact outgoing control bytes:

```python
bytes.fromhex("5a a5 80 00 01 00 00 00 7f")
```

For expansion on/off, assert payloads `01` and `00` under command `0x91`.

- [ ] **Step 2: Verify failure**

Run: `PYTHONPATH=src pytest -q tests/test_aic_usb_controls.py`

Expected: FAIL because backend controls do not exist.

- [ ] **Step 3: Implement conservative capabilities and controls**

Add an immutable module-level capability value for the currently supported device:

```python
_AIC_33C3_0E02_CAPABILITIES = DisplayCapabilities(
    hardware_brightness=True,
    device_version=True,
    panel_info=True,
    expansion_mode=True,
)
```

Implement control sends through a small private helper rather than duplicating USB writes. Never emit `0x85` or control `0x86` from public methods.

Store the last known Expansion Screen Mode from a valid panel-info response so `get_expansion_mode()` can return it without fabricating a value.

- [ ] **Step 4: Keep existing connection/streaming behavior intact**

Do not remove the existing vendor `ctrl_transfer` parameter query or RSA authentication. Device-control enrichment happens after the existing connection succeeds, and failure to retrieve optional version/state metadata must not corrupt `_dev` or the JPEG stream.

- [ ] **Step 5: Run focused tests**

Run: `PYTHONPATH=src pytest -q tests/test_aic_usb_controls.py tests/test_protocol.py tests/test_streaming.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/owndash/hardware/aic_usb.py tests/test_aic_usb_controls.py
git commit -m "feat: add ArtInChip display controls"
```

### Task 4: Display control UI

**Files:**
- Create: `src/owndash/gui/display_controls.py`
- Modify: `src/owndash/gui/main_window.py`
- Modify: `src/owndash/i18n.py`
- Test: `tests/test_display_controls.py`

**Interfaces:**
- Consumes: connected `DisplayBackend`, `DisplayInfo`, `DisplayCapabilities`.
- Produces: `DisplayControlsWidget` that hides unsupported controls and delegates supported changes to the backend.

- [ ] **Step 1: Write offscreen Qt tests**

Tests should instantiate `DisplayControlsWidget` with a fake backend and verify:

- device name/resolution text is visible;
- version text is displayed when capability/value exists;
- brightness slider is visible only when `hardware_brightness=True`;
- expansion checkbox is visible only when `expansion_mode=True`;
- slider changes call `set_brightness` with integer percent;
- checkbox changes call `set_expansion_mode` with a bool;
- `DisplayProtocolError` is surfaced as non-fatal status text.

Run under `QT_QPA_PLATFORM=offscreen`.

- [ ] **Step 2: Verify failure**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest -q tests/test_display_controls.py`

Expected: FAIL because widget does not exist.

- [ ] **Step 3: Implement focused widget**

Create `DisplayControlsWidget(QWidget)` in its own file rather than growing `main_window.py` further. Constructor receives the backend and current `DisplayInfo`; `refresh_from_backend()` reads capabilities and optional state.

Use copy that never implies true power-off. Brightness is labeled `Brightness`/localized equivalent and range is exactly 0-100.

- [ ] **Step 4: Integrate in main window**

Add the control widget to the existing display/settings area only after a backend connects. On disconnect, clear/disable it. Do not let UI exceptions stop the streaming timer or shutdown path.

- [ ] **Step 5: Add i18n strings**

Add translations for `Display`, `Device version`, `Brightness`, `Expansion Screen Mode`, and concise control-error text in the project's existing i18n structure.

- [ ] **Step 6: Run GUI tests**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest -q tests/test_display_controls.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/owndash/gui/display_controls.py src/owndash/gui/main_window.py src/owndash/i18n.py tests/test_display_controls.py
git commit -m "feat: add display control panel"
```

### Task 5: Regression verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md` if present; otherwise do not create a duplicate roadmap file.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: user-facing documentation and a fully verified branch.

- [ ] **Step 1: Document only implemented controls**

Add a short README section stating that compatible ArtInChip displays can expose device information, hardware brightness, and Expansion Screen Mode. Explicitly avoid advertising startup-image upload until its separate phase is implemented.

- [ ] **Step 2: Run compile verification**

Run: `python -m compileall -q src`

Expected: exit 0.

- [ ] **Step 3: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 4: Run shell syntax checks used by CI**

Run the repository's existing `bash -n` checks exactly as defined in `.github/workflows`.

Expected: exit 0.

- [ ] **Step 5: Commit docs**

```bash
git add README.md ROADMAP.md 2>/dev/null || git add README.md
git commit -m "docs: describe display controls"
```

- [ ] **Step 6: Hardware verification before merge**

On the real `33C3:0E02` display, verify native resolution/version, brightness at 100/50/0 and restored normal value, Expansion Screen Mode round-trip if observable, normal JPEG streaming, and Safe Shutdown.

- [ ] **Step 7: Merge only after CI and hardware verification are green**

Merge `feature/display-control-capabilities` into `main`, then run/verify `main` CI again. Remove temporary feature branches/workflow clutter when supported, matching the project's clean-repository policy.
