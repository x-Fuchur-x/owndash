# Device Detection Profiles & Multi-Device Safety Design

## Goal

Make OwnDash direct-USB device detection easier to extend and safer for community hardware without enabling any new unverified hardware command.

The current supported ArtInChip / VSDISPLAY path (`33C3:0E02`) is implemented in several modules with duplicated VID/PID constants. Passive probes also return the first matching sysfs entry. This slice introduces one authoritative USB device profile, deterministic passive detection, and explicit reporting when more than one compatible device is present.

## Principles

- One source of truth for supported USB identities.
- No broad wildcard matching and no claim that unknown ArtInChip product IDs are compatible.
- Detection and Device Center refresh remain read-only.
- Existing single-device `33C3:0E02` streaming behavior stays compatible.
- Multiple compatible devices must never be silently presented as one unambiguous device.
- The profile model must make adding a future verified VID/PID a small, testable change.
- Diagnostic reports must not include USB serial numbers or other unique identifiers by default.

## Device profile registry

Add `src/owndash/hardware/usb_device_profiles.py` with an immutable `UsbDeviceProfile` model.

Each profile owns:

- stable profile key;
- human-readable name;
- integer vendor/product IDs for PyUSB;
- normalized lowercase sysfs IDs;
- uppercase `VID:PID` display text.

The initial registry contains exactly one verified profile:

- key: `artinchip-33c3-0e02`
- name: `ArtInChip / VSDISPLAY 33C3:0E02`
- VID: `0x33C3`
- PID: `0x0E02`

`aic_usb.py`, `usb_setup.py`, `aic_usb_inventory.py`, diagnostics, and future support code must consume this profile rather than repeat numeric/string constants.

## Passive sysfs detection

The sysfs inventory probe remains passive and must not import PyUSB, open a device, claim an interface, detach a kernel driver, authenticate, or send data.

It should collect all exact matches for the selected verified profile in deterministic sysfs-name order.

The existing `ArtInChipUsbInventory` gains non-breaking fields with defaults:

- `profile_key`
- `profile_name`
- `vid_pid`
- `match_count`
- `ambiguous`

For zero matches: `status="absent"`, `match_count=0`, `ambiguous=False`.

For one match: existing inventory details are populated, `status="present"`, `match_count=1`, `ambiguous=False`.

For multiple matches: the first sorted match may still supply representative read-only interface data, but `match_count>1` and `ambiguous=True` must make the ambiguity explicit. No serial number is collected.

## USB access probe

`UsbAccessStatus` gains `match_count` and `ambiguous` fields with defaults so existing positional construction remains compatible.

The probe scans deterministic exact profile matches. It reports:

- no matches: disconnected;
- one match: current access semantics unchanged;
- multiple matches: connected, representative node/access data, `match_count>1`, `ambiguous=True`.

The access probe does not choose a preferred persistent device identity.

## Streaming safety

The PyUSB backend must not silently choose an arbitrary display when more than one verified compatible device is connected.

`AicUsbDisplayBackend.connect()` should request all exact profile matches. If none exist, keep the existing not-found error. If more than one exists, raise a dedicated display-selection ambiguity error before claiming interfaces or sending any USB command. With exactly one device, existing connection/authentication behavior is unchanged.

Add `DisplayAmbiguousError` under the display error hierarchy and classify it separately in diagnostics as `ambiguous`.

## Device Center

For the direct-USB backend, Device Center should show:

- supported profile name;
- VID:PID;
- matching compatible devices count;
- detected/access status;
- representative device node;
- an explicit ambiguity state when more than one compatible device exists.

The copyable diagnostic report includes profile key/name, match count, and ambiguity, but not serial numbers.

For non-USB backends these fields stay absent rather than fabricated.

## Compatibility

- Public renderer/display APIs are unaffected.
- The single-device `33C3:0E02` path must keep working exactly as before.
- Existing `UsbAccessStatus(connected, accessible, node)` constructions remain valid through defaulted new fields.
- Existing `ArtInChipUsbInventory(...)` constructions remain valid through defaulted new fields.
- udev rule behavior is unchanged except that rule generation/probing reads the VID/PID from the central profile.
- No new USB IDs become supported in this slice.

## Verification

Automated tests must cover:

1. Profile formatting and exact-ID matching.
2. Single-device sysfs inventory compatibility.
3. Multiple-device passive inventory count and ambiguity.
4. Deterministic representative match selection.
5. USB access probe multiple-device reporting.
6. PyUSB connection refusal before claim/control operations when multiple devices match.
7. Diagnostics `ambiguous` error classification.
8. Device Center profile/match/ambiguity presentation.
9. Diagnostic report profile fields and privacy boundary.
10. Full existing suite, compile check, AppImage compatibility and Debian 12 smoke test.
