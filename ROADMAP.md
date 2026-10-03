# OwnDash Roadmap

OwnDash is evolving from a Linux dashboard editor with direct ArtInChip / VSDISPLAY support into a broader customizable hardware-dashboard platform.

This roadmap describes direction rather than fixed delivery dates. Priorities may change as hardware testing, community feedback, and technical constraints uncover better paths.

## Completed in 0.14.0 Beta 5

Beta 5 concentrates on safer display behavior, clearer diagnostics and release-quality lifecycle handling:

- Always-available Display & Device Center with passive, sanitized diagnostics and explicit capability states
- Central verified direct-USB device profiles and deterministic refusal to select an arbitrary device when multiple compatible displays are present
- Software dimming that affects only OwnDash output and never pretends to be hardware backlight control
- Clear selected-output versus active-output state across direct USB and standard-monitor paths
- Responsive system-state rendering across ultra-portrait, portrait, near-square and landscape targets, with the 480×1920 VSDISPLAY as the protected physical reference
- Runtime-owned localized state text and version footer, plus a 48-image CI preview matrix
- State-aware time policy: live time only on lock/idle; no stale clock/date on standby, shutdown, restart or disconnected final frames
- Manual update checks with explicit user-initiated feedback while background failures remain silent and OwnDash never auto-installs updates

Released features and full details remain documented in [`CHANGELOG.md`](CHANGELOG.md).

## Completed in 0.14.0 Beta 4

Beta 4 closed several items that were previously listed as upcoming work:

- Proportional widget-content scaling across geometry, fonts, spacing, borders and effects
- Persisted fitted geometry and content scaling across saves, reloads and theme changes
- Improved monitor selection, HiDPI resolution reporting and editor fitting
- Adaptive portrait/landscape pause screens with contextual status and localization
- Safe pause-frame handling when switching away from direct USB output
- Improved USB write validation and disconnect handling
- Optional, non-blocking update checks with user-facing release notifications
- Capability-driven UI groundwork for optional device controls, with unsupported controls kept hidden

Released features and full historical details remain documented in [`CHANGELOG.md`](CHANGELOG.md).

## Now — 0.14.x Beta Stabilization

The current priority is making the public beta increasingly predictable across real Linux systems and supported display paths.

- Beta bug fixes and regression prevention
- Continued real-device validation across additional Linux distributions, desktops, compositors and display hardware
- Validation of mixed-DPI and compositor-specific fullscreen behavior on additional real systems
- AppImage packaging, clean-user testing and release reliability
- Diagnostics and setup polish where community feedback shows real friction
- Preserve the single responsive system-state renderer and its protected 480×1920 hardware reference while expanding community evidence for other aspect ratios

The project's Bazzite/KDE + VSDISPLAY lifecycle path has been rechecked after the responsive renderer work. Beta 5's final release-candidate smoke test includes the state-aware static-time policy before publication.

The system-state implementation, unified renderer architecture and resource behavior are documented in [`docs/system-state-screens.md`](docs/system-state-screens.md).

## In progress — 0.15 Device Experience

Make connected displays easier to understand and control without exposing unsupported hardware functions.

Foundational 0.15-oriented work already landed during the 0.14.x beta stabilization cycle:

- Always-available **Display & Device** Device Center, including when no display is connected
- Passive ArtInChip / VSDISPLAY presence, USB-access, device-node and OwnDash-udev diagnostics
- A central registry of verified direct-USB device profiles, with exact VID/PID matching instead of duplicated or vendor-wide assumptions
- Deterministic multi-device diagnostics that report compatible match counts and ambiguity explicitly
- Direct-USB safety that refuses to choose an arbitrary compatible display when multiple exact matches are connected
- Current and session-only last-known device state, connection times and categorized display errors
- Explicit capability states that distinguish **available**, **unsupported**, and **not yet verified**
- Sanitized, copyable diagnostic reports intended for GitHub issues and support
- Read-only refresh behavior protected by regressions so diagnostics do not connect, reconnect, send frames or issue hardware-control writes
- Universal **Software dimming** from 10–100% that darkens the rendered image without pretending to control display backlight hardware
- Consistent display-management summary across direct USB and standard-monitor output, separating the **selected output**, actually **active output**, and current connection state
- Clear separation between **OwnDash software features** and **Hardware capabilities**, including a visible saved software-dimming value even when no output is active
- A dedicated Display-menu management group for **Device Information** and **Software dimming**
- A shared read-only key/value layout standard so Device Center and system/sensor information dialogs align labels and current values in consistent vertical columns
- AppImage CI coverage for `feat/**` branches so feature builds can be tested against the Debian 12 / GLIBC compatibility baseline before integration
- Update-notification polish with a manual **Check for updates** action, explicit up-to-date/error feedback for user-initiated checks, silent background failures, and no automatic download or installation

Remaining 0.15 work:

- Add further direct-USB device profiles only after exact hardware/transport verification and beta evidence
- Hardware brightness control only where the selected backend and real hardware expose a verified mechanism
- Expansion Screen Mode only after the connected device and transport have been verified safely
- Persistent startup-image support only after a separate real-hardware verification phase

The current `33C3:0E02` ArtInChip path deliberately keeps hardware brightness, Expansion Screen Mode and startup-media writes disabled until real-device evidence proves a safe transport. Software dimming is intentionally separate: it modifies only OwnDash's rendered image and sends no new hardware-control command. The Device Center reports hardware capability states explicitly instead of implying support that has not been proven. Display-management behavior is documented in [`docs/device-center.md`](docs/device-center.md).

## Planned — 0.16 Dashboard Studio

Expand visual flexibility without turning the editor into a complicated design suite.

- More instrument and gauge styles
- Additional animation presets
- Dashboard-page transition effects
- More templates and reusable visual starting points
- Continued editor usability and workflow polish
- Contextual controls that keep advanced options out of the way until they are useful

## Planned — 0.17 Sensors & Automation

Make dashboards react more intelligently to the system they represent.

- Broader Linux telemetry and hardware-sensor coverage
- Richer sensor-driven rules and warnings
- More flexible alert behavior and visual states
- Automated dashboard and scene behavior based on sensor conditions
- Better handling and explanation of optional or unavailable metrics

## Exploring — 0.18+ Platform Expansion

OwnDash should not be limited to one proprietary USB display family.

- Investigate additional proprietary USB display protocols
- Add new display backends where protocols can be supported reliably and legally
- Broaden practical testing across Linux distributions, desktops, GPUs, and hardware configurations
- Improve backend capability reporting so hardware-specific features degrade gracefully

Items in this section are exploratory until protocol feasibility and real hardware have been validated.

## Ongoing — Performance & Architecture

Performance and maintainability continue alongside feature development.

- Measure CPU use and render behavior on real devices
- Continue tuning adaptive output cadence
- Investigate render and JPEG encoding paths that avoid unnecessary duplicate work
- Improve USB streaming efficiency where measurements show a real benefit
- Keep display backends isolated behind clear interfaces
- Keep exactly one production system-state renderer path; state and orientation differences belong inside that renderer, not in separate implementations or versioned renderer branches
- Keep system-state geometry driven by aspect-ratio layout profiles and runtime data rather than per-resolution or per-device special cases
- Split oversized GUI responsibilities when related feature work benefits from smaller, testable components

OwnDash will favor targeted refactoring over a rewrite. Existing working behavior should remain protected by automated tests.

## Road to 1.0

A 1.0 release should represent a dependable baseline rather than simply the next version number.

Before 1.0, the project aims to have:

- Stable configuration and migration behavior
- Strong regression coverage for core editor, sensor, and display workflows
- Reliable AppImage build and release checks
- Clearly documented Linux and hardware compatibility expectations
- Predictable first-run, diagnostics, update, and display-management behavior
- A defined stable feature set that can evolve without breaking existing dashboards unnecessarily
