# OwnDash Changelog

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
