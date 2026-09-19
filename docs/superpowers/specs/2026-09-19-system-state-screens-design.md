# System State Screens Design

## Goal

Add first-class Linux/Bazzite system-state awareness to OwnDash so the display can react meaningfully to suspend, resume, shutdown, restart, session lock, unlock, idle, and user activity without coupling those events directly to the editor UI or display backend.

The feature should feel native to OwnDash, remain safe when Linux system-state APIs are unavailable, and be easy to extend later with additional context such as gaming mode, updates, network state, or other operating-system events.

## Scope for Beta 5

Beta 5 includes these states and transitions:

- Active
- Idle
- Locked
- Suspending
- Resume
- Shutting down
- Restarting
- Unlock / user activity return

Two selectable visual presets are included:

- **OwnDash** — the existing OwnDash neon/HUD visual language.
- **Bazzite-inspired** — a dark blue/violet gaming-Linux style that visually fits Bazzite without bundling the official Bazzite logo or other copied brand assets.

Resume does not show a separate welcome screen. The previous dashboard is restored immediately after resume.

## Out of Scope for Beta 5

The following are explicitly deferred:

- Automatic game detection and game-specific dashboards
- Network offline/online overlays
- Update-available or reboot-required indicators
- Dynamic USB brightness control
- Vendor firmware boot-image management
- Official Bazzite logo integration
- Windows or macOS system-state support

The architecture should leave room for these features later without requiring a rewrite.

## Architecture

### SystemStateManager

Introduce a platform-facing `SystemStateManager` responsible only for detecting and normalizing system events.

On Linux/Bazzite, the preferred source is systemd-logind / D-Bus. The manager converts platform-specific signals into a small internal state model and emits state changes to the rest of OwnDash.

The manager must not render UI, write to USB devices, or know about dashboard widgets.

Proposed normalized states:

- `ACTIVE`
- `IDLE`
- `LOCKED`
- `SUSPENDING`
- `SHUTTING_DOWN`
- `RESTARTING`

Resume, unlock, and return-from-idle are transitions back to `ACTIVE` rather than persistent states.

### State priority

When multiple conditions overlap, the visible state is chosen using this priority:

1. `SHUTTING_DOWN` / `RESTARTING`
2. `SUSPENDING`
3. `LOCKED`
4. `IDLE`
5. `ACTIVE`

This prevents a lower-priority state such as idle from replacing a more important state such as suspend or shutdown.

### SystemStateScreenRenderer

Introduce a renderer that creates a complete frame for system-state screens.

Inputs:

- normalized system state
- selected theme preset
- display width and height
- portrait / landscape orientation
- application language
- current date/time where relevant
- optional small sensor values for idle/locked screens

The renderer must not communicate with D-Bus or USB hardware. It produces a frame using the same output path OwnDash already uses for normal dashboard frames.

### Display output integration

The existing display-output layer remains responsible for sending the rendered frame to the selected destination.

For direct ArtInChip/VSDISPLAY USB output, OwnDash sends the system-state frame immediately before suspend/shutdown when possible.

For standard monitor output, the same rendered screen is shown through the normal display window path.

No system-state event may block OS suspend, restart, or shutdown indefinitely.

## State Behaviour

### Active

Normal dashboard rendering continues unchanged.

### Idle

Idle is a low-distraction mode, not a warning screen.

Default presentation:

- very dark background
- minimal or no animation
- clock
- optional CPU/GPU temperature values
- no large status message

Returning user activity restores the prior dashboard immediately.

This is a visual low-activity mode only. It does not claim to reduce backlight power on hardware that lacks brightness control.

### Locked

Locked is distinct from idle because the session has intentionally been secured.

Default presentation:

- clock
- date
- localized `System locked` text
- OwnDash branding
- optional small temperature value

Unlocking restores the prior dashboard immediately.

### Suspending

When the system announces imminent suspend, OwnDash renders and attempts to send a final standby frame before sleep begins.

Default presentation:

- localized `Standby` / `Entering standby` message
- selected visual preset
- OwnDash branding

If the USB display retains the last frame while the host sleeps, the standby screen remains visible. If the USB bus loses power or the display controller resets, OwnDash cannot guarantee persistence and must not delay suspend trying to preserve it.

### Resume

On resume, OwnDash immediately restores the dashboard that was active before suspend.

There is no dedicated `Welcome back` screen in Beta 5.

The display backend should be allowed to reconnect or reinitialize before normal updates resume when needed.

### Shutdown

When the operating system is shutting down, OwnDash renders a dedicated shutdown frame distinct from the normal application-close screen.

The current application-close screen remains appropriate when the user exits OwnDash while the computer continues running.

### Restart

Restart uses a dedicated `Restarting` screen so a reboot is visually distinguishable from a normal shutdown.

## Themes

### OwnDash preset

Uses OwnDash's established neon/HUD visual identity and existing branding assets.

### Bazzite-inspired preset

Uses a dark gaming-oriented presentation with blue/violet accents and modern Linux styling.

Requirements:

- do not include the official Bazzite logo in Beta 5
- do not copy Bazzite artwork or proprietary brand assets
- label the preset `Bazzite-inspired` rather than presenting it as an official Bazzite theme
- keep the rendering implementation independent so official assets could be added later if explicit permission is obtained

## Settings

Add a system-state-screen section to OwnDash settings with at minimum:

- enable/disable system-state screens
- theme preset: `OwnDash` or `Bazzite-inspired`
- enable/disable idle mode
- idle timeout setting
- enable/disable lock screen handling where supported

Suspend/resume/shutdown/restart handling should be enabled by default on supported Linux systems once the feature is considered stable.

## Failure Handling

System-state integration is optional infrastructure. OwnDash must continue operating normally if it is unavailable.

Required behaviour:

- If D-Bus or systemd-logind is unavailable, OwnDash logs the condition and continues with normal dashboard operation.
- If a state event cannot be delivered to the display, OwnDash records the failure but does not block the OS transition.
- If the USB display disconnects during suspend or resume, normal reconnect logic handles recovery.
- Repeated or duplicate D-Bus events must not cause duplicate transitions or corrupt the previous-dashboard state.
- Unexpected events fall back to the safest valid state rather than crashing the application.

## State Restoration

Before entering any temporary system-state screen, OwnDash preserves enough runtime information to restore the user's previous dashboard view.

At minimum this includes the active dashboard/page and the intended display destination.

On resume, unlock, or return from idle, OwnDash restores that view without forcing the user back to a default page.

## Internationalization

All visible state text must use the existing OwnDash localization system.

Initial English and German strings should cover at least:

- Standby
- Entering standby
- System locked
- Shutting down
- Restarting

Theme names and settings labels must also be localized where the rest of the settings UI is localized.

## Testing

Automated tests should cover:

- state-priority rules
- active -> idle -> active
- active -> locked -> active
- idle -> locked priority
- locked/idle -> suspend priority
- suspend -> resume restoration
- shutdown vs restart distinction
- duplicate events
- missing D-Bus/systemd-logind
- display unavailable during transition
- USB disconnect/reconnect around suspend/resume
- portrait and landscape rendering
- OwnDash and Bazzite-inspired presets
- English and German strings

Where direct D-Bus integration is difficult to exercise in CI, the platform adapter should be mockable so the normalized state logic and rendering can be tested independently.

## Manual Validation on Bazzite

Before release, validate on the primary Bazzite + KDE Plasma test system with both:

- direct ArtInChip/VSDISPLAY USB output
- standard Linux monitor output

Manual checks should confirm:

- final standby frame is sent before suspend
- actual hardware behaviour while suspended is documented: frame retained, display off, or controller reset
- dashboard returns correctly after resume
- KDE session lock/unlock is detected correctly
- idle mode exits immediately on activity
- restart and shutdown screens are visually distinguishable
- no system transition is noticeably delayed by OwnDash

## Future Extension Points

The normalized-state design should make it possible to add later event families without changing the renderer/output boundary:

- game-running / gaming profile
- network offline/online
- update available / reboot required
- media playback
- hardware alerts
- device disconnect/reconnect status

These future events should be added only when they provide a clear display benefit rather than turning OwnDash into a general desktop notification system.

## Success Criteria

The feature is successful when:

1. OwnDash reliably detects the supported Bazzite/Linux states without destabilizing the application.
2. The display shows the correct system-state screen according to the priority rules.
3. Suspend, shutdown, and restart are never blocked by display handling.
4. Resume, unlock, and activity return restore the prior dashboard automatically.
5. Both visual presets work in portrait and landscape modes.
6. OwnDash remains fully usable when system-state integration is unavailable.
7. The architecture can later support gaming and other context-aware states without coupling OS detection directly to rendering or hardware code.
