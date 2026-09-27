# System state screens

OwnDash can replace the normal dashboard with a lightweight status view when the Linux session changes state. The feature is designed for small internal PC displays and direct USB sensor panels where leaving a busy dashboard running during lock, idle or standby is unnecessary.

## Implementation status

The lifecycle behavior is functionally implemented for idle, lock, suspend/standby, shutdown and restart. State detection, priority handling, timer pausing/restoration and bounded direct-USB resume recovery are covered by automated tests and have been exercised on the project's Bazzite/KDE + VSDISPLAY development setup.

The visual renderer has now been rebuilt as one unified OwnDash HUD family. It no longer depends on the previous embedded portrait master artwork. The new renderer uses the packaged OwnDash application logo, shared geometry, state-specific symbols and accents, a large HUD ring and a consistent footer/branding language across portrait and landscape output. The disconnected/closed OwnDash screen delegates to the same visual family instead of maintaining separate artwork.

The primary visual reference is the project's 480×1920 portrait VSDISPLAY. Automated tests enforce exact requested output dimensions, but final visual acceptance still requires physical Bazzite/KDE + VSDISPLAY inspection so spacing and perceived scale can be tuned on the real panel before release.

## Renderer architecture rule

System-state output has exactly **one production renderer path**. Visual work must refine that path rather than adding another renderer generation alongside it.

Allowed variation belongs behind explicit state, orientation or theme configuration within the current renderer. The project must not reintroduce versioned renderer implementations, hidden package-level monkeypatches, duplicate fallback renderers or separate experimental production paths.

The former embedded status-master loader and its data chunks have been removed. There is deliberately no fallback to the retired artwork: a renderer regression should fail visibly in tests rather than silently showing an obsolete design.

Visual experiments are fine during development, but before integration they must either be folded into the single current renderer or removed. Regression tests describe current intended geometry and behavior rather than preserving obsolete design generations.

## Visual design language

The unified renderer uses the real packaged OwnDash logo and a common HUD structure for all states. State identity comes from the symbol, wording and accent rather than a different layout implementation for each screen.

Current accents are:

- lock: cyan / blue
- idle: green / teal
- standby: amber / orange
- shutdown: red
- restart: violet
- disconnected / OwnDash closed: neutral OwnDash blue-violet treatment

Portrait output uses one shared geometric system for the logo/header, HUD ring, state symbol, headline, detail text, optional clock/date, lower HUD geometry and version footer. Landscape output is derived from the same design family rather than treated as a separate renderer.

## States and priority

OwnDash normalizes Linux lifecycle events into these states:

1. `ACTIVE`
2. `IDLE`
3. `LOCKED`
4. `SUSPENDING`
5. `SHUTTING_DOWN` / `RESTARTING`

Higher-priority states temporarily hide lower-priority states. For example, if the session is locked and the machine then suspends, the standby screen replaces the lock screen. After resume, the lock screen remains visible until the session is actually unlocked.

## Linux integration

The Linux backend uses Qt D-Bus with `systemd-logind` and systemd Manager signals. It subscribes to events instead of running a polling loop.

OwnDash currently listens for:

- `PrepareForSleep` for suspend and resume
- session `Lock` / `Unlock` as best-effort lock/unlock request signals
- session `LockedHint` once at startup and then through D-Bus `PropertiesChanged`, so the actual session lock state stays synchronized without polling
- `PrepareForShutdown` for terminal shutdown handling
- systemd `JobNew` plus logind `ScheduledShutdown` as positive evidence for restart/reboot

Restart is intentionally conservative: OwnDash only shows the restart state when there is positive reboot evidence. An ambiguous terminal event is treated as shutdown instead of guessing.

If Qt D-Bus, logind or a required session object is unavailable, OwnDash fails open: the normal dashboard continues to work and system-state screens simply remain unavailable.

## Idle detection

Idle handling is event-driven. OwnDash reads logind's system idle information and only arms a single-shot Qt timer after the session has already become idle and the configured OwnDash delay still needs to expire.

There is no continuously running idle polling timer. The user-configurable idle delay is 1–240 minutes, with 30 minutes as the default.

## Resource behavior and HUD animation

When a system-state screen becomes visible, OwnDash stops recurring dashboard work that is not useful for the status view:

- live sensor refresh timer
- normal display rendering/output timer
- automatic dashboard-page cycling timer

Persistent `IDLE` and `LOCKED` views may run one dedicated low-rate HUD animation timer. It currently advances the ring at a 750 ms cadence and submits non-blocking status frames. This is intentionally much lighter than keeping normal dashboard rendering and sensor updates active.

Suspend, shutdown, restart and other terminal lifecycle frames remain static. Their `animation_phase` is deliberately ignored so terminal transitions retain the bounded, deterministic final-frame behavior required for lifecycle safety.

On resume or unlock, OwnDash stops the HUD animation, restores the timers that had actually been active before the transition and immediately pushes a fresh dashboard frame.

## Suspend and shutdown safety

OwnDash does not acquire a systemd sleep or shutdown inhibitor for this feature.

The final terminal state frame is best-effort and uses a short bounded wait (currently 250 ms) for the display sender. A slow or disconnected display must not meaningfully delay system suspend or shutdown.

Display-I/O errors during a system transition are contained and do not abort the operating-system lifecycle event.

## USB resume recovery

Some direct USB displays disappear from the USB bus while the machine sleeps. For the ArtInChip / VSDISPLAY backend, OwnDash treats a disconnect during suspend or immediately after resume as a recoverable lifecycle event:

- the failed stream is released quietly
- no suspend-time warning-dialog spam is shown
- after resume, one bounded reconnect sequence is scheduled
- there is no reconnect polling loop or endless retry loop
- a normal manual display stop cancels pending recovery state

If reconnect succeeds while the session is still locked or idle, OwnDash sends the appropriate system-state HUD rather than briefly flashing the normal dashboard.

## Themes and localization

Two visual treatments are currently available:

- `OwnDash`
- `Bazzite-inspired`

The Bazzite-inspired theme is an original OwnDash visual treatment and does not bundle or reproduce third-party Bazzite logos or artwork. Both themes use the real OwnDash application logo.

System-state labels, runtime status messages and settings participate in OwnDash's German/English localization system.

## Settings

The general settings dialog exposes:

- master switch for system-state screens
- visual theme
- idle mode enable/disable
- idle timeout
- lock-screen handling

Settings are stored in the normal OwnDash preferences file. Existing Beta 4 preference files migrate automatically to safe defaults.

## Compatibility and testing

Automated tests cover state priority, duplicate-event suppression, lock/suspend/resume ordering, output dimensions, state-specific visuals, removal of the retired embedded-master path, persistent HUD animation, static terminal frames, shared disconnected-screen rendering, preference migration, exact D-Bus signal signatures, initial and live `LockedHint` detection, timer pause/restore behavior, localized lifecycle status messages and direct-USB resume recovery.

Real suspend/resume behavior can still vary with firmware, USB controllers, desktop sessions and compositor behavior. Release acceptance therefore includes physical Bazzite/KDE + VSDISPLAY checks in addition to automated CI and AppImage checks. The current unified HUD is the release candidate design, but its final pixel-level spacing remains subject to that physical 480×1920 review.