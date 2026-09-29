# Device Detection Profiles & Multi-Device Safety Implementation Plan

## Scope

Implement the approved design in small TDD steps without adding any unverified device-control command.

## Task 1 — Central verified USB profile

Files:
- add `src/owndash/hardware/usb_device_profiles.py`
- add `tests/test_usb_device_profiles.py`

RED:
- require one verified `33C3:0E02` profile;
- require stable key/name, integer IDs, sysfs IDs and uppercase display VID:PID;
- require exact profile lookup and no wildcard compatibility.

GREEN:
- implement frozen `UsbDeviceProfile` and exact lookup helpers.

## Task 2 — Passive inventory multi-match awareness

Files:
- modify `src/owndash/hardware/aic_usb_inventory.py`
- modify `tests/test_aic_usb_inventory.py`

RED:
- require profile metadata in inventory;
- require deterministic sorted representative selection;
- require `match_count` and `ambiguous=True` for two exact matches.

GREEN:
- replace duplicated IDs with the central profile;
- collect exact matches before constructing the representative inventory.

## Task 3 — Access probe multi-match awareness

Files:
- modify `src/owndash/hardware/usb_setup.py`
- modify/add tests around USB setup/probing.

RED:
- require deterministic matching count and ambiguity without changing one-device access semantics.

GREEN:
- extend `UsbAccessStatus` with defaulted `match_count`/`ambiguous`;
- scan sorted exact matches and use profile-owned IDs in udev trigger commands.

## Task 4 — Streaming refuses ambiguous hardware selection

Files:
- modify `src/owndash/core/display.py`
- modify `src/owndash/hardware/aic_usb.py`
- modify `tests/test_aic_usb_transfers.py` or add focused backend tests.

RED:
- require zero matches => existing not-found;
- one match => normal connection path;
- two matches => dedicated `DisplayAmbiguousError` before interface claim/control/authentication.

GREEN:
- add `DisplayAmbiguousError`;
- use the profile IDs and `find(..., find_all=True)`;
- convert result to a bounded tuple and enforce exactly one compatible device.

## Task 5 — Diagnostics and Device Center

Files:
- modify `src/owndash/service/device_diagnostics.py`
- modify `src/owndash/gui/display_controls.py`
- modify `src/owndash/gui/device_center_window.py` translations
- modify diagnostics/device-center tests.

RED:
- require `ambiguous` error category;
- require profile name/key, match count and ambiguity in AIC snapshots/reports;
- require Device Center labels and translated presentation.

GREEN:
- extend immutable snapshot with default-safe fields;
- derive live fields from passive probe/inventory only;
- show new rows only for USB diagnostics.

## Task 6 — Documentation and roadmap

Files:
- modify `docs/device-center.md`
- modify `ROADMAP.md`
- modify `CHANGELOG.md`
- update README files only if user-facing setup wording materially changes.

Document:
- central profile registry;
- exact-match support policy;
- multiple-device safety refusal;
- no new supported VID/PIDs and no new hardware writes.

## Task 7 — Verification and integration gate

Run on exact final head:
- `python -m compileall -q src tests tools`
- `pytest -q`
- `bash -n run-owndash.sh`
- GitHub Tests workflow
- AppImage build
- GLIBC compatibility verification
- Debian 12 AppImage smoke test

Review the branch diff for:
- accidental new hardware writes;
- wildcard device matching;
- serial-number leakage;
- backward-incompatible dataclass constructors;
- duplicated VID/PID constants that should use the profile.

Only after all checks are green should the branch be proposed for integration.
