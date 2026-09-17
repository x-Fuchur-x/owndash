# Display Control & Capabilities Design

## Goal

Add a safe, capability-driven control layer for compatible ArtInChip/VSDISPLAY USB displays, starting with device information, hardware brightness, and Expansion Screen Mode. Keep startup-media upload as the next isolated phase after these controls are hardware-verified.

## Scope

This phase covers only behavior confirmed by static interoperability analysis for the supported `VID 0x33C3 / PID 0x0E02` family path:

- Device capabilities as explicit data instead of scattered PID conditionals.
- Device/panel information reporting.
- Hardware brightness using the confirmed 0-100% UI to 0-255 device mapping.
- Device-version query support.
- Expansion Screen Mode read/set support when the device capability says it is supported.
- Protocol parsing/building kept independent from Qt UI code.

Out of scope for this phase:

- Raw flash, EEPROM, XDATA, or firmware flashing.
- The dormant/unknown control command `0x86`.
- Claiming brightness 0% is power-off or sleep.
- Startup JPG/MP4 upload implementation; it will be a separate follow-up after this phase is verified on hardware.
- H.264 transport changes.

## Safety and interoperability boundaries

OwnDash must implement the observed protocol independently. No vendor DLL, executable code, icons, themes, images, or other proprietary assets are copied into the project.

Only documented/verified control messages are exposed. Unknown commands remain internal notes and are not sent to hardware.

## Architecture

Introduce a small immutable capability model in the core display layer. `DisplayInfo` remains the connection result but gains optional version/capability/state metadata without forcing unrelated display backends to implement ArtInChip-specific behavior.

Keep ArtInChip control-packet serialization/parsing in `owndash.hardware.aic_protocol`. The USB backend owns transport and connection lifecycle. High-level control methods validate capability support before emitting bytes.

The first implementation should not add a second independent device connection. It must reuse the existing backend lifecycle and preserve the current frame-streaming path.

## Capability model

Add `DisplayCapabilities` with conservative defaults. Fields for this phase:

- `hardware_brightness: bool`
- `device_version: bool`
- `panel_info: bool`
- `expansion_mode: bool`
- `startup_image: bool = False`
- `startup_video: bool = False`
- `hardware_screen_off: bool = False`
- `firmware_upgrade: bool = False`

For the currently supported `33C3:0E02` backend, enable the first four only. Startup-media fields stay false until the separate upload feature is implemented and hardware-tested.

## Control protocol

Use the confirmed small control frame layout:

`5A A5 <command> 00 <payload_length:u32 little-endian> <payload>`

Confirmed commands for this phase:

- `0x80`: set hardware brightness, one-byte payload.
- `0x81`: query device version; response payload is UTF-8 text.
- `0x90`: query panel information; response carries native width/height and the Expansion Screen Mode state for the supported device path.
- `0x91`: set Expansion Screen Mode, one-byte `0`/`1` payload.

Brightness mapping is `floor(percent * 255 / 100)` with accepted input `0..100`.

Do not use `0x85` or `0x86` in user-facing control methods in this phase.

## Backend interface

Add optional control methods to `DisplayBackend` with default `DisplayProtocolError` behavior so existing screen backends remain source-compatible:

- `get_capabilities() -> DisplayCapabilities`
- `get_device_version() -> str | None`
- `set_brightness(percent: int) -> None`
- `get_expansion_mode() -> bool | None`
- `set_expansion_mode(enabled: bool) -> None`

The ArtInChip backend overrides supported methods. Unsupported backends keep safe defaults.

## UI

Expose a compact Display Control section only when a connected backend reports matching capabilities. This phase should show:

- Connected device name and native resolution.
- Device version when available.
- Brightness slider `0..100`.
- Expansion Screen Mode toggle when supported.

No Power Off wording is used. Brightness 0% is labeled and treated only as brightness 0%.

UI operations must surface transport failures without crashing the streamer or blocking normal shutdown.

## Testing

Protocol tests are pure unit tests with no hardware:

- frame construction for `0x80`, `0x81`, `0x90`, `0x91`;
- brightness boundary/mapping tests;
- device-version UTF-8 response parsing;
- panel-info width/height and expansion-mode parsing;
- malformed/short response rejection;
- unsupported capability methods fail safely.

Backend tests use fake USB/transport objects and assert exact outgoing bytes. Existing JPEG/authentication tests must remain unchanged.

Hardware verification is a manual final gate after CI is green:

1. Connect the real `33C3:0E02` display.
2. Confirm version/native resolution readout.
3. Verify brightness at 100%, 50%, and 0%, then restore a comfortable value.
4. Toggle Expansion Screen Mode only if the current display state makes the effect observable; restore the original value.
5. Verify normal streaming and Safe Shutdown still work.

## Follow-up

After this phase is merged and hardware-verified, implement Startup Image as a separate feature using the already reconstructed persistent-media protocol. That feature must keep raw flash APIs out of OwnDash.