# OwnDash Roadmap

OwnDash is evolving from a Linux dashboard editor with direct ArtInChip / VSDISPLAY support into a broader customizable hardware-dashboard platform.

This roadmap describes direction rather than fixed delivery dates. Priorities may change as hardware testing, community feedback, and technical constraints uncover better paths.

## Now — 0.14.x Beta Stabilization

The current priority is making the public beta increasingly predictable across real Linux systems and supported display paths.

- Safe display shutdown and a defined end state when OwnDash is fully quit
- Beta bug fixes and regression prevention
- Continued real-device validation
- Linux distribution, desktop, sensor, and display compatibility improvements
- AppImage packaging and release reliability
- Diagnostics and setup polish where beta feedback shows friction

## Next — 0.15 Update & Device Experience

Make OwnDash easier to maintain and make connected displays easier to understand and control.

- Background update check with a clear user-facing notification when a new OwnDash release is available
- Release information and a safe path to obtain the new version
- Capability-driven device information for compatible ArtInChip displays
- Hardware brightness control where the selected backend and hardware expose a verified mechanism
- Expansion Screen Mode where the connected device reports support
- Improved display and device detection
- Clearer diagnostics for unavailable, unsupported, or permission-limited devices
- More consistent display-management UX across direct USB and standard-monitor output
- Persistent startup-image support after a separate real-hardware verification phase

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

## Completed work

Released features and historical version details are maintained in [`CHANGELOG.md`](CHANGELOG.md).
