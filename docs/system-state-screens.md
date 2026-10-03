# System state screens

OwnDash can replace the normal dashboard with a lightweight status view when the Linux session changes state. The feature is designed for small internal PC displays and direct USB sensor panels where leaving a busy dashboard running during lock, idle or standby is unnecessary.

## Implementation status

The lifecycle behavior is functionally implemented for idle, lock, suspend/standby, shutdown and restart. State detection, priority handling, timer pausing/restoration and bounded direct-USB resume recovery are covered by automated tests and have been exercised on the project's Bazzite/KDE + VSDISPLAY development setup.

The visual renderer uses one approved family of lossless state PNG source sheets plus runtime-owned localized state wording, clock/date and the current OwnDash version. The disconnected/closed OwnDash screen delegates to the same renderer family instead of maintaining a separate visual implementation.

The project's physically accepted 480×1920 VSDISPLAY remains the protected visual reference. That exact target keeps its approved composition. Other dimensions are composed responsively from target-relative zones instead of containing a narrow 1:4 screen inside unused space.

## Renderer architecture rule

System-state output has exactly **one production renderer path**. Visual work must refine that path rather than adding another renderer generation alongside it.

Allowed variation belongs behind explicit state or responsive-layout handling within the current renderer. The project must not reintroduce versioned renderer implementations, hidden package-level monkeypatches, duplicate fallback renderers or separate experimental production paths.

The former embedded status-master loader, master asset and obsolete data chunks have been removed. There is deliberately no fallback to the retired artwork: a renderer regression should fail visibly in tests rather than silently showing an obsolete design.

Visual experiments are fine during development, but before integration they must either be folded into the single current renderer or removed. Regression tests describe current intended geometry and behavior rather than preserving obsolete design generations.

## Responsive layout model

The renderer classifies the requested logical output size from its aspect ratio. It does not maintain a list of known display resolutions.

- `ultra_portrait`: aspect ratio below 0.38
- `portrait`: 0.38 up to, but not including, 0.78
- `near_square`: 0.78 through 1.25
- `landscape`: above 1.25

Each class provides target-relative safe zones for the HUD artwork, state title, detail text, optional clock/date, accent and version footer. The resulting image always has the exact dimensions requested by the caller.

The protected 480×1920 reference stays vertically stacked. Ordinary portrait layouts use their additional width, near-square layouts balance artwork and information, and landscape layouts use a horizontal composition with the HUD on the left and information on the right. Extremely wide or tall valid sizes still go through the same threshold model and safe-zone constraints rather than receiving device-specific exceptions.

## Runtime-owned content

Mutable content is owned by OwnDash at runtime:

- localized state title and optional detail text
- clock/date only where the state can be actively refreshed
- `OwnDash {__version__}` footer
- animation phase for the states that support it

Changing from Beta 4 to Beta 5, an RC, a stable release or a later version therefore requires no system-state artwork edit. The footer always reads the central OwnDash version at render time.

The approved 480×1920 source sheets predate the strict runtime-only wording rule and contain generated state copy in their full composition. OwnDash never treats that wording as authoritative: the protected reference path masks and redraws it, while responsive layouts use the text-free HUD/symbol region and draw all visible copy themselves. New reusable artwork must not add mutable text, dates, clock values or release numbers.

Detail copy may use at most two lines in responsive layouts. Titles remain single-line when their zone allows it, with font fitting applied inside the assigned safe area. Clock and date are optional modules; when both are absent, no empty clock panel is painted.

The time policy is deliberately state-aware: `LOCKED` may show live clock and date, `IDLE` may show the live clock without a date, and suspend/standby, transition, shutdown, restart and disconnected/closed screens show neither. This prevents a static final frame from presenting a clock that can no longer be updated.

## Visual design language

All states use the same structural HUD language while keeping their own approved symbol and accent treatment:

- lock: cyan / magenta
- idle: cyan / green
- standby: amber / gold
- shutdown: red
- restart: violet / magenta
- disconnected / OwnDash closed: cyan / magenta

German and English UI strings remain authoritative and are rendered at runtime rather than being selected from pre-rendered language-specific screens.

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

Automated tests cover state priority, duplicate-event suppression, lock/suspend/resume ordering, exact output dimensions, responsive aspect-ratio classification, safe-zone containment, localized runtime copy, bounded detail wrapping, state-specific visuals, dynamic version/footer rendering, removal of retired master artifacts, persistent HUD animation, static terminal frames, shared disconnected-screen rendering, preference migration, exact D-Bus signal signatures, initial and live `LockedHint` detection, timer pause/restore behavior, localized lifecycle status messages and direct-USB resume recovery.

CI also renders a 48-image production preview matrix: six states across 480×1920, 720×1280, 800×1280, 1024×1024, 1024×600, 1280×800, 1920×1080 and 2560×1440. These previews are uploaded as one workflow artifact for visual review.

Real suspend/resume behavior can still vary with firmware, USB controllers, desktop sessions and compositor behavior. The responsive-refactor lifecycle was rechecked on the project's 480×1920 Bazzite/KDE + VSDISPLAY setup; the Beta 5 release-candidate smoke test also covers the final static-time policy. Other aspect ratios are accepted through structural tests and visual review of the production preview matrix, with community hardware reports remaining valuable follow-up evidence.
