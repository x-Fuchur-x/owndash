# OwnDash Roadmap

OwnDash is evolving from a Linux dashboard editor with direct ArtInChip / VSDISPLAY support into a broader customizable hardware-dashboard platform.

This roadmap describes direction rather than fixed delivery dates. Priorities may change as hardware testing, community feedback, and technical constraints uncover better paths.

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
- Event-driven system-state screens for idle, lock, suspend, shutdown and restart are functionally implemented; final visual layout/artwork polish and physical Bazzite/KDE + VSDISPLAY validation remain before release
- Finalize system-state visual layout and artwork on the **single production renderer path**; new visual iterations must refine that renderer instead of introducing parallel renderer generations, hidden fallbacks or version-specific rendering paths
- Static system-state output already pauses unnecessary sensor refresh, display rendering and dashboard cycling while a state screen is visible
- Direct-USB suspend/resume recovery already uses a bounded one-shot reconnect instead of background polling
- Continued real-device validation, especially output switching and shutdown/end-state behavior
- Linux distribution, desktop, sensor, and display compatibility improvements
- AppImage packaging and release reliability
- Diagnostics and setup polish where beta feedback shows friction
- Validation of mixed-DPI and compositor-specific fullscreen behavior on additional real systems

The system-state implementation and its fallback/resource behavior are documented in [`docs/system-state-screens.md`](docs/system-state-screens.md).

## In progress — 0.15 Device Experience

Make connected displays easier to understand and control without exposing unsupported hardware functions.

The first 0.15 slice is implemented on the current feature work:

- Always-available **Display & Device** Device Center, including when no display is connected
- Passive ArtInChip / VSDISPLAY presence, USB-access, device-node and OwnDash-udev diagnostics
- Current and session-only last-known device state, connection times and categorized display errors
- Explicit capability states that distinguish **available**, **unsupported**, and **not yet verified**
- Sanitized, copyable diagnostic reports intended for GitHub issues and support
- Read-only refresh behavior protected by regressions so diagnostics do not connect, reconnect, send frames or issue hardware-control writes
- Universal **Software dimming** from 10–100% that darkens the rendered image without pretending to control display backlight hardware
- AppImage CI coverage for `feat/**` branches so feature builds can be tested against the Debian 12 / GLIBC compatibility baseline before integration

Remaining 0.15 work:

- More consistent display-management UX across direct USB and standard-monitor output
- Further device-detection improvements based on real beta hardware feedback
- Hardware brightness control only where the selected backend and real hardware expose a verified mechanism
- Expansion Screen Mode only after the connected device and transport have been verified safely
- Persistent startup-image support only after a separate real-hardware verification phase
- Update-notification polish based on beta feedback, while keeping downloads and installation user-controlled

The current `33C3:0E02` ArtInChip path deliberately keeps hardware brightness, Expansion Screen Mode and startup-media writes disabled until real-device evidence proves a safe transport. Software dimming is intentionally separate: it modifies only OwnDash's rendered image and sends no new hardware-control command. The Device Center reports hardware capability states explicitly instead of implying support that has not been proven.

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
- Keep exactly one production system-state renderer path; visual variants belong behind explicit theme/state configuration, not separate renderer implementations or versioned renderer branches
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