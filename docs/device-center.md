# Device Center and display management

OwnDash keeps display selection, output status, software-only controls and hardware capability diagnostics deliberately separate. The goal is to make the current display state understandable without implying that unverified hardware commands are available.

## Where to find it

Open the **Display** menu. **Device Information …** and **Software dimming …** form one dedicated display-management group, separated from display start/selection and background-runtime actions.

**Device Information …** remains available even when no display is currently connected or streaming.

## Output summary

The top **Output** section distinguishes three related facts:

- **Selected output** — the backend OwnDash is configured to use, for example `ArtInChip / VSDISPLAY` or `Standard monitor`.
- **Active output** — the output that is actually connected and running. When nothing is running, OwnDash says **No active output** instead of presenting the selected backend as connected.
- **Connection** — the current connected/not-connected state.

This distinction is intentional. A configured backend can remain selected while its hardware is disconnected or while output is stopped.

## OwnDash features vs. hardware capabilities

The Device Center separates **OwnDash features** from **Hardware capabilities**.

**Software dimming** is an OwnDash feature. It darkens the rendered image before normal output and does not change display backlight hardware. Its current saved percentage is shown in the Device Center even when no output is active.

Hardware capabilities are reported independently as:

- **Available** — the selected backend exposes a verified implementation.
- **Unsupported** — the backend/device combination does not provide that capability in OwnDash.
- **Not yet verified** — OwnDash deliberately does not expose the operation because the real transport or behavior has not been proven safely.

For the current ArtInChip / VSDISPLAY `33C3:0E02` path, hardware brightness, Expansion Screen Mode and persistent startup-media writes remain disabled until real-device evidence proves a safe compatible transport. Software dimming must not be presented as hardware brightness.

## USB and diagnostic information

For compatible direct-USB hardware, Device Information can show passive evidence such as VID:PID, device detection, access state, device node, OwnDash udev-rule state and the sysfs USB interface/endpoint inventory.

Refreshing this information is read-only. The Device Center does not connect or reconnect the display, claim interfaces, authenticate, send frames, issue hardware-control writes, flash firmware or modify persistent device storage.

The **Copy diagnostic report** action produces a sanitized support report. Usernames, home-directory paths, environment dumps, logs and secrets are not intentionally included.

## Software dimming

Open **Display → Software dimming …** to choose 10–100%.

- `100%` leaves the outgoing image unchanged.
- Lower values darken the rendered image in software.
- Changes preview live while the dialog is open.
- **Apply** stores the value in normal OwnDash preferences.
- **Cancel** restores the previous value.

Dimming uses the existing image/JPEG output path only. It does not send a new device-control command.

## Display backends

OwnDash currently exposes two main output paths:

- **ArtInChip / VSDISPLAY** — compatible direct USB display output.
- **Standard monitor** — a display Linux/Qt already recognizes as a normal screen.

The summary uses the same selected-vs-active model for both paths so future backends can follow one consistent display-management UX.

## Maintenance rule

Whenever display behavior changes, update this help page together with the user-facing README/README_DE, changelog and roadmap where applicable. Capability wording must continue to distinguish software features, verified hardware features, unsupported behavior and behavior that is merely unverified.
