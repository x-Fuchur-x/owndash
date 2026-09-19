# OwnDash Changelog

## Unreleased

## 0.14.0 Beta 4

- Widget fonts, spacing, borders and effects now scale proportionally with their geometry.
- Fitted geometry and content scaling survive saving, reloading and theme changes.
- Corrected monitor selection, HiDPI resolution reporting and editor fitting.
- Added a responsive pause screen with portrait and landscape layouts, clearer text, a contextual reason and the running version.
- Pause screens follow dashboard orientation and the selected German or English UI language.
- Switching away from USB replaces frozen telemetry with a pause screen.
- Improved USB write validation and disconnect handling.
- Unsupported hardware controls remain disabled; USB brightness and firmware boot-image replacement are not enabled.

- Added an optional background check for newer OwnDash releases on the official GitHub repository.
- Update checks are enabled by default and can be disabled in Settings.
- Update checks are non-blocking, use a short network timeout, and fail silently when GitHub or the network is unavailable.
- Stable builds ignore prereleases; beta builds can detect newer betas as well as newer stable releases.
- Available updates are shown with a modeless notification that can open the corresponding GitHub release page.
- OwnDash does not download, install, or replace the AppImage automatically at this stage.

## 0.14.0 Beta 3

- Official AppImages are now built on a Debian 12 compatibility baseline.
- Release CI verifies that bundled ELF binaries require no newer than GLIBC 2.36.
- The finished AppImage is launched in a clean Debian 12 environment as an automated compatibility smoke test.
- Added AppStream metadata for improved Linux desktop and application metadata integration.
- Improved AppImage packaging metadata and desktop application categorization.
- Documentation now clearly distinguishes practical hardware testing from automated AppImage compatibility testing.
- Documented the x86-64 and GLIBC 2.36 minimum baseline for the official AppImage.
- Clarified that Python and PySide6 do not need to be installed separately when using the AppImage.
- Clarified the difference between official Debian 12 release builds and locally built AppImages.
- Project metadata now describes OwnDash as a customizable Linux hardware dashboard platform rather than a USB-only telemetry application.
- Documentation now more clearly distinguishes standard Linux monitor output from compatible direct USB display support.

## 0.14.0 Beta 2

- VRAM widgets automatically use the detected total VRAM for GiB scales.
- VRAM units display correctly, with one decimal place for GiB values.
- Unavailable gauge sensors no longer fall back to unrelated CPU/GPU readings.
- AMDGPU VRAM usage, used GiB and total GiB are available in the existing widget sensor selector.
- Sensor diagnostics report VRAM availability. Missing, unreadable or invalid counters remain unavailable, not zero.
- VRAM currently uses AMDGPU sysfs counters; NVIDIA/Intel VRAM and real-device verification remain follow-up work.

## 0.14.0 Beta 1 — First Public Beta

This is the first public beta of OwnDash. It combines the completed internal development work into one clear public starting point.

- Beginner-friendly first-run system and compatibility check.
- Dynamic Linux sensor discovery for CPU/GPU usage, temperature and power where supported.
- System and sensor diagnostics with dark/light/system theme support.
- ArtInChip/VSDISPLAY direct USB output with access-permission detection and graphical udev setup.
- Standard Linux monitor output with fullscreen safety and Esc/F11 exit.
- Multi-dashboard editor with themes, templates, gauges, charts, animations, rules and live output.
- German and English interface with System/Light/Dark appearance modes.
- Single-instance behavior and optional tray background mode.
- GitHub help, About, changelog and prefilled bug-report workflow.
- AppImage build tooling, automated tests and release checklist.
- Fixed animated widgets losing selection during frame export.
- Fixed first-run layout compression and several KDE visual seams.
- Localized dialog close buttons now follow the selected OwnDash language.

## 0.13.2 — Fullscreen Safety
- Confirmation before standard-monitor fullscreen output.
- Extra warning for the primary monitor.
- Esc/F11 exits fullscreen output safely.

## 0.13.1 — Safe Display Switching
- Stops the old output backend before switching target, resolution or rotation.

## 0.13.0 — Universal Display Platform
- Added display backend abstraction and standard Linux monitor output.
- Added dynamic dashboard canvas sizes.

## 0.12.5 — Single Instance
- A second OwnDash launch activates the existing process instead of starting another one.

## 0.12.x — Localization & UI Polish
- German/English localization, System/Light/Dark appearance and extensive UI consistency work.

## 0.11.x — Multi-Dashboard
- Multiple dashboard pages, cycling and editor polish.

## 0.10.x — Motion & Rules
- Animation triggers, alert rules and additional motion effects.

## 0.9.x — Editor, Backgrounds & Performance
- Background transform tools, snapping, layers, animations, tray runtime and render optimizations.

## 0.8.0 — Dashboard Studio
- Charts, sparklines, sensor binding, gauge styles, templates and additional themes.

## 0.6.0 — Direct Display Output
- First direct ArtInChip USB output from OwnDash.
