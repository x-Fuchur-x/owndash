# Device Center & Diagnostics Design

## Goal

Introduce a read-only **Device Center** that is always available, even when no display is connected, so OwnDash can clearly answer:

- What display/backend is configured or detected?
- Is the supported ArtInChip/VSDISPLAY device physically present?
- Does the current user have access to it?
- Which output path and rotation are configured?
- Which features are truly available, unsupported, or merely not yet verified?
- What was the last successful device state?
- What was the last display-related error?

This phase deliberately does **not** add hardware brightness, Expansion Screen Mode, startup-image writing, firmware operations, or any other unverified device-write command.

The primary success criterion is that a user can open one place in OwnDash and understand the current display situation without having to inspect the terminal, while normal JPEG streaming, suspend/resume recovery, shutdown behavior, and display switching remain unchanged.

## Context

OwnDash already has:

- `DisplayCapabilities` and `DisplayInfo` in the hardware-independent display model;
- passive ArtInChip USB probing that reports presence, access and device node;
- lifecycle state in `SafeShutdownWindow` for active connections, reconnects and errors;
- a capability-driven `DisplayControlsWidget` intended for optional hardware controls.

The current `33C3:0E02` backend intentionally reports no optional hardware-control capabilities because no compatible write/control transport has been verified on the owner's real device. The Device Center must preserve that conservative behavior.

An earlier display-control design that assumed a CDC/serial control path is superseded and must not be revived by this work.

## Scope

### Included

1. Always-available Device Center entry point.
2. Read-only live diagnostics for the currently configured display backend.
3. Passive USB detection/access information for the supported ArtInChip path.
4. Last-known connection information and last display error for the current OwnDash session.
5. Three-state capability presentation:
   - `available`
   - `unsupported`
   - `unverified`
6. A sanitized, copyable diagnostic report.
7. Explicit distinction between live state and last-known state.
8. Headless automated tests proving the Device Center does not perform write/control operations.

### Out of scope

- Hardware brightness writes.
- Expansion Screen Mode reads/writes that require an unverified transport.
- Persistent startup image/video writing.
- Firmware update or raw flash/EEPROM/XDATA access.
- Automatic reconnect from the Device Center.
- Claiming or opening the USB interface during a manual diagnostic refresh.
- Persisting diagnostics history across OwnDash restarts in phase 1.
- General system log collection.

Session-only last-known state is intentional for phase 1. It keeps the feature deterministic and avoids storing stale hardware/error history on disk. Persistent history can be considered later if real beta feedback shows value.

## UX

The existing user-facing concept `Display-Steuerung …` becomes a broader **Display & Gerät …** / **Display & Device …** Device Center.

The entry remains visible and enabled regardless of current connection state.

The window contains four read-only sections.

### 1. Gerät / Device

Show:

- current connection status;
- backend name/key;
- connected device name when known;
- native resolution when known;
- reported refresh/FPS when known;
- configured output mode;
- configured rotation.

When no current connection exists, last-known device information is shown in a clearly secondary form rather than pretending it is live.

Example:

- `Nicht verbunden`
- `Zuletzt erkannt: USB Bar Display · 1920×480`
- `Letzte erfolgreiche Verbindung: 10:42:18`

### 2. USB & Zugriff / USB & Access

For `aic_usb`, show the passive probe result:

- VID:PID `33C3:0E02`;
- detected yes/no;
- accessible yes/no/unknown;
- current `/dev/bus/usb/...` device node when available;
- udev state:
  - `ok`
  - `legacy`
  - `missing`
  - `unknown`

The Device Center must not open PyUSB, claim an interface, authenticate, reconnect, or send a frame merely to refresh this section.

For non-AIC backends, this section shows only relevant backend-level information and does not fabricate USB fields.

### 3. Funktionen / Capabilities

Capabilities are not represented as booleans in the UI. Each row uses one of three semantic states:

- **available** — verified and currently exposed by the active backend;
- **unsupported** — known not to exist for the selected backend/device path;
- **unverified** — OwnDash intentionally does not expose the function because support has not been proven safely on this hardware/transport.

For the current `33C3:0E02` path in phase 1:

- JPEG streaming: `available` when the backend itself is supported;
- Hardware brightness: `unverified`;
- Expansion Screen Mode: `unverified`;
- Startup image: `unverified`;
- Startup video: `unverified`;
- Hardware screen off: `unverified` unless future protocol evidence proves otherwise;
- Firmware upgrade: `unsupported` as an OwnDash feature unless a future explicitly scoped feature changes that policy.

This distinction is important: `unverified` must never be rendered as `unsupported`, because the former communicates a safety/evidence boundary rather than a hardware impossibility.

### 4. Letzte Aktivität / Last Activity

Show:

- last successful connection timestamp;
- last disconnect timestamp;
- last categorized display error;
- last error text;
- last-known device information.

This data is maintained for the current OwnDash process lifetime and survives ordinary disconnects/reconnect attempts within that session.

### Actions

The footer contains:

- `Aktualisieren` / `Refresh`
- `Diagnosebericht kopieren` / `Copy diagnostic report`
- `Schließen` / `Close`

`Refresh` performs only passive checks and reads current in-memory state. It must not reconnect or mutate hardware state.

## Architecture

### Existing display model remains authoritative

`src/owndash/core/display.py` remains the authoritative backend-independent model for `DisplayInfo`, `DisplayCapabilities`, and transport exceptions.

No ArtInChip-specific fields are added to `DisplayInfo` solely for the Device Center.

### New diagnostics service

Add `src/owndash/service/device_diagnostics.py`.

Its responsibilities are:

- hold current-session last-known device state;
- accept lifecycle events from `SafeShutdownWindow`;
- gather passive backend/system state;
- classify errors into stable categories;
- map backend capabilities into UI-facing semantic capability states;
- produce an immutable diagnostic snapshot;
- format a sanitized diagnostic report.

The service must not own the display backend and must not start/stop streaming.

Suggested immutable model:

```python
class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"

class DeviceErrorCategory(StrEnum):
    NOT_FOUND = "not_found"
    PERMISSION = "permission"
    BUSY = "busy"
    PROTOCOL = "protocol"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class DeviceDiagnosticSnapshot:
    backend_key: str
    backend_name: str
    connected: bool
    device_detected: bool | None
    accessible: bool | None
    device_node: str | None
    usb_vid_pid: str | None
    device_name: str | None
    native_width: int | None
    native_height: int | None
    refresh_hz: int | None
    rotation: int | None
    output_mode: str
    udev_state: str
    capabilities: dict[str, CapabilityStatus]
    last_connected_at: datetime | None
    last_disconnected_at: datetime | None
    last_error_category: DeviceErrorCategory | None
    last_error_message: str | None
    last_known_info: DisplayInfo | None
```

The exact internal representation of `capabilities` may use tuples or another immutable mapping if that makes testing/typing cleaner; UI semantics are fixed by this spec.

### SafeShutdownWindow integration

`SafeShutdownWindow` owns one diagnostics service instance and reports lifecycle events to it:

- successful display connection;
- explicit stop/disconnect;
- display error;
- backend/output selection changes when relevant.

`SafeShutdownWindow` must not grow formatting or USB-inspection logic. Its role is event forwarding and opening the Device Center.

### Device Center widget

Refactor `src/owndash/gui/display_controls.py` into the Device Center presentation layer rather than creating a second overlapping device dialog.

The widget receives diagnostic snapshots and renders them. It does not directly probe hardware or own connection lifecycle.

Future verified controls may later be added as an additional capability-gated section in the same Device Center, but phase 1 remains read-only.

## Data flow

### Opening Device Center while disconnected

1. User opens `Display & Gerät …`.
2. Window asks diagnostics service for a fresh snapshot.
3. Service calls only passive probes appropriate to the configured backend.
4. Service combines live probe data with session last-known state.
5. Device Center renders the snapshot.

No display backend connection is started.

### Opening while streaming

1. User opens Device Center during active output.
2. Service reads existing in-memory `DisplayInfo`/backend capability state.
3. Passive system/USB probe may run.
4. Stream remains owned by the existing streamer.
5. Device Center renders without claiming or reopening the device.

### Disconnect/error

1. Existing display lifecycle detects the error/disconnect.
2. Window reports it to diagnostics service before clearing transient connection state.
3. Service stores categorized error and last-known information.
4. Device Center later shows both current disconnected state and previous known device details.

### Refresh

Refresh replaces only the live portion of the snapshot. It does not erase last-known history unless a newer successful connection replaces it.

## Error classification

Phase 1 does not introduce a large new exception hierarchy. The diagnostics service classifies existing exceptions and error text conservatively.

Stable categories:

- `not_found` — compatible device absent;
- `permission` — device detected but current user cannot access it;
- `busy` — another process/service owns the device;
- `protocol` — authentication/protocol/USB transaction failure;
- `disconnected` — device vanished during active use;
- `unknown` — unexpected failure that cannot be classified safely.

Where the passive USB probe can establish a stronger fact than generic exception text, the probe wins. Example: detected=true and accessible=false should be presented as an access/permission condition rather than a generic protocol failure.

User-facing wording is localized and concise. The diagnostic report retains the stable category plus the sanitized message.

## Diagnostic report

The report is plain text suitable for pasting into a GitHub issue.

It includes:

- OwnDash version;
- backend key/name;
- connection state;
- output mode and rotation;
- device name/resolution/FPS when known;
- USB VID:PID, presence, access, device node and udev state for AIC USB;
- capability states;
- last successful connection/disconnect timestamps;
- last error category and sanitized message;
- high-level Linux/session context that is already available without collecting logs.

It must not include:

- usernames;
- home-directory paths;
- arbitrary environment-variable dumps;
- full system logs;
- secrets, tokens, keys or private configuration contents.

Device-node paths such as `/dev/bus/usb/001/006` are allowed because they are directly relevant to diagnosis and contain no user identity.

## Capability policy

The diagnostics layer must not infer hardware support from device family alone when support has not been verified.

`DisplayCapabilities` continues to answer "what OwnDash currently exposes as supported". The diagnostics layer adds the separate concept of `unverified` for features that are intentionally disabled pending evidence.

This allows the UI to be honest without losing future direction.

A future feature that becomes hardware-verified must update both:

1. backend capability exposure; and
2. diagnostic capability policy/tests.

## Testing strategy

### Pure service tests

Add tests for:

- snapshot with no detected device;
- detected but inaccessible device;
- detected and accessible device;
- legacy udev rule;
- active connection;
- disconnect retaining last-known data;
- reconnect replacing last-known information;
- each stable error category;
- capability mapping to `available`, `unsupported`, `unverified`;
- report formatting;
- report sanitization.

### GUI tests

Headless Qt tests verify:

- Device Center action is always available;
- dialog opens with no active connection;
- disconnected state renders useful information;
- last-known information remains visible after disconnect;
- refresh updates visible snapshot;
- copy action places the expected report on the clipboard;
- no hardware-control widgets are interactive in phase 1.

### Non-interference regressions

Add explicit regressions proving:

- opening Device Center while streaming does not stop the display timer;
- refreshing does not call backend `connect()`;
- refreshing does not call `send_jpeg()`;
- refreshing does not call brightness/expansion setters;
- refreshing does not claim/release the USB interface;
- existing suspend/resume reconnect behavior remains unchanged;
- existing Safe Shutdown/system-state behavior remains unchanged.

Use fakes/mocks that fail immediately if a forbidden mutating method is called.

## Files expected to change

Primary files:

- `src/owndash/service/device_diagnostics.py` — new diagnostics service/model/report formatting
- `src/owndash/gui/display_controls.py` — refactor into Device Center UI
- `src/owndash/gui/app_window.py` — lifecycle event forwarding and always-available menu action
- `src/owndash/i18n.py` — localized Device Center strings
- `tests/test_device_diagnostics.py` — service/report tests
- `tests/test_display_controls.py` — Device Center GUI tests
- relevant existing lifecycle regression tests

Possible small supporting changes:

- `src/owndash/hardware/usb_setup.py` if udev-state reporting needs a pure helper rather than duplicating rule-state logic;
- `ROADMAP.md` / `CHANGELOG.md` after implementation is verified.

No change to the ArtInChip transport protocol is required for phase 1.

## Quality boundaries

- Read-only means read-only: no hardware mutation is allowed from this feature.
- The Device Center must remain useful when the device is absent.
- Diagnostics must never block normal app startup.
- Passive refresh failures are rendered as diagnostic state, not modal crashes.
- Existing direct USB streaming behavior takes precedence over richer diagnostics.
- Avoid expanding `main_window.py`; keep lifecycle integration in `SafeShutdownWindow` and diagnostics logic in the dedicated service.
- Preserve the project's targeted-refactoring approach; no rewrite.

## Acceptance criteria

Phase 1 is complete when:

1. `Display & Gerät …` is always available.
2. It opens and provides useful information with no display connected.
3. It distinguishes current state from last-known state.
4. It reports ArtInChip detection/access/udev state passively.
5. It presents `available`, `unsupported`, and `unverified` capabilities distinctly.
6. It retains the current session's last device information and last categorized error after disconnect.
7. It can copy a sanitized diagnostic report.
8. Automated tests prove refresh/open operations do not mutate hardware state or interrupt streaming.
9. Existing full CI remains green.
10. Real-device validation confirms opening and refreshing the Device Center does not disturb the active VSDISPLAY stream.
