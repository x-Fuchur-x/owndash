# System state screens

OwnDash can replace the normal dashboard with a lightweight status view when the Linux session changes state. The feature is designed for small internal PC displays and direct USB sensor panels where leaving a busy dashboard running during lock, idle or standby is unnecessary.

## Implementation status

The lifecycle behavior is functionally implemented for idle, lock, suspend/standby, shutdown and restart. State detection, priority handling, timer pausing/restoration and bounded direct-USB resume recovery are covered by automated tests and have been exercised on the project's Bazzite/KDE + VSDISPLAY development setup.

The visual renderer uses one approved family of lossless state PNGs plus runtime overlays for localized state wording, clock/date and the current OwnDash version. The disconnected/closed OwnDash screen delegates to the same renderer family instead of maintaining a separate visual implementation.

The primary visual reference is the project's 480×1920 portrait VSDISPLAY. That portrait artwork is never stretched. If a different aspect ratio is requested, OwnDash scales the complete 1:4 artwork proportionally, centers it on a matching dark canvas and maps all runtime overlays into the same contained geometry.

## Renderer architecture rule

System-state output has exactly **one production renderer path**. Visual work must refine that path rather than adding another renderer generation alongside it.

Allowed variation belongs behind explicit state or orientation handling within the current renderer. The project must not reintroduce versioned renderer implementations, hidden package-level monkeypatches, duplicate fallback renderers or separate experimental production paths.

The former embedded status-master loader, master asset and obsolete data chunks have been removed. There is deliberately no fallback to the retired artwork: a renderer regression should fail visibly in tests rather than silently showing an obsolete design.

Visual experiments are fine during development, but before integration they must either be folded into the single current renderer or removed. Regression tests describe current intended geometry and behavior rather than preserving obsolete design generations.

## Visual design language

All states use the same structural HUD language while keeping their own approved symbol and accent treatment:

- lock: cyan / magenta
- idle: cyan / green
- standby: amber / gold
- shutdown: red
- restart: violet / magenta
- disconnected / OwnDash closed: cyan / magenta

The source artwork intentionally leaves clock/date/version areas free. State title/detail text is redrawn at runtime so German and English UI language remain authoritative rather than being locked to wording baked into the source image.

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

On resume or unlock, OwnDash stops the HUD animation, restores the timers that had actually been active before the state transition and immediately pushes a fresh dashboard frame.

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

## Localization and visual preference compatibility

System-state labels and runtime status messages participate in OwnDash's German/English localization system.

The current approved system-state artwork is intentionally one visual family. The previous system-state theme selector has therefore been removed rather than presenting a control with no visible effect. Existing saved `system_state_theme` values remain readable and are preserved for configuration compatibility, but they do not recolor or replace the approved artwork.

## Settings

The general settings dialog exposes:

- master switch for system-state screens
- idle mode enable/disable
- idle timeout
- lock-screen handling

Settings are stored in the normal OwnDash preferences file. Existing Beta 4 preference files continue to load safely.

## Compatibility and testing

Automated tests cover state priority, duplicate-event suppression, lock/suspend/resume ordering, exact output dimensions, aspect-preserving non-portrait rendering, localized runtime state copy, state-specific visuals, removal of retired master artifacts, persistent HUD animation, static terminal frames, shared disconnected-screen rendering, preference migration, exact D-Bus signal signatures, initial and live `LockedHint` detection, timer pause/restore behavior, localized lifecycle status messages and direct-USB resume recovery.

Real suspend/resume behavior can still vary with firmware, USB controllers, desktop sessions and compositor behavior. Release acceptance therefore includes physical Bazzite/KDE + VSDISPLAY checks in addition to automated CI and AppImage checks. The current HUD is the release-candidate design, but final physical pixel-level review remains separate from automated verification.
