# System state screens

OwnDash can replace the normal dashboard with a lightweight static status frame when the Linux session changes state. The feature is designed for small internal PC displays and direct USB sensor panels where leaving a busy animated dashboard running during lock, idle or standby is unnecessary.

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
- session `Lock` / `Unlock`
- session `LockedHint` once at startup, so starting OwnDash while the desktop is already locked is handled correctly
- `PrepareForShutdown` for terminal shutdown handling
- systemd `JobNew` plus logind `ScheduledShutdown` as positive evidence for restart/reboot

Restart is intentionally conservative: OwnDash only shows the restart state when there is positive reboot evidence. An ambiguous terminal event is treated as shutdown instead of guessing.

If Qt D-Bus, logind or a required session object is unavailable, OwnDash fails open: the normal dashboard continues to work and system-state screens simply remain unavailable.

## Idle detection

Idle handling is also event-driven. OwnDash reads logind's system idle information and only arms a single-shot Qt timer after the session has already become idle and the configured OwnDash delay still needs to expire.

There is no continuously running idle polling timer.

The user-configurable idle delay is 1–240 minutes. The default is 30 minutes.

## Resource behavior

System-state screens are static by design. When one becomes visible, OwnDash stops its recurring work that is not useful for a static state frame:

- live sensor refresh timer
- display rendering/output timer
- automatic dashboard-page cycling timer

One status JPEG is rendered and submitted. Normal dashboard rendering is suppressed until the effective state returns to `ACTIVE`.

On resume or unlock, OwnDash restores the timers that had actually been active before the state transition and immediately pushes a fresh dashboard frame.

This design avoids running decorative animation loops while the PC is idle, locked or entering standby.

## Suspend and shutdown safety

OwnDash does not acquire a systemd sleep or shutdown inhibitor for this feature.

The final state frame is best-effort and uses a short bounded wait (currently 250 ms) for the display sender. A slow or disconnected display must not meaningfully delay system suspend or shutdown.

Display-I/O errors during a system transition are contained and do not abort the operating-system lifecycle event.

## USB resume recovery

Some direct USB displays disappear from the USB bus while the machine sleeps. For the ArtInChip / VSDISPLAY backend, OwnDash treats a disconnect during suspend (or immediately after resume) as a recoverable lifecycle event:

- the failed stream is released quietly
- no suspend-time warning-dialog spam is shown
- after resume, one delayed reconnect attempt is scheduled
- there is no reconnect polling loop or endless retry loop
- a normal manual display stop cancels pending recovery state

If the reconnect succeeds while the session is still locked or idle, OwnDash sends the appropriate system-state screen rather than briefly flashing the normal dashboard.

## Themes and localization

Two built-in static visual treatments are currently available:

- `OwnDash`
- `Bazzite-inspired`

The Bazzite-inspired theme is an original OwnDash visual treatment and does not bundle or reproduce third-party Bazzite logos or artwork.

System-state labels and settings participate in OwnDash's German/English localization system.

## Settings

The general settings dialog exposes:

- master switch for system-state screens
- visual theme
- idle mode enable/disable
- idle timeout
- lock-screen handling

Settings are stored in the normal OwnDash preferences file. Existing Beta 4 preference files migrate automatically to safe defaults.

## Compatibility and testing

Automated tests cover state priority, duplicate-event suppression, lock/suspend/resume ordering, static frame rendering, preference migration, D-Bus signal signatures, initial lock-state detection, timer pause/restore behavior and direct-USB resume recovery.

Real suspend/resume behavior can still vary with firmware, USB controllers, desktop sessions and compositor behavior. Release acceptance therefore includes a physical Bazzite/KDE + VSDISPLAY test in addition to automated CI and AppImage checks.
