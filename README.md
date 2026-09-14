# OwnDash

### Your display. Your design.
**A visual Linux hardware dashboard editor — without the terminal headache.**

![OwnDash Dashboard Editor](docs/images/owndash-editor.png)

OwnDash lets you create customizable hardware-monitoring dashboards for dedicated PC displays and secondary monitors — visually, without having to understand Python, `hwmon`, USB protocols or Linux internals.

> **OwnDash 0.14.0 Beta 2 is now available.**
>
> Download the ready-to-run x86-64 AppImage from the [latest OwnDash release](https://github.com/x-Fuchur-x/owndash/releases/tag/v0.14.0-beta.2).

## OwnDash in action

![OwnDash running on a PC sensor display](docs/images/owndash-hardware.jpg)

The first public beta has been tested on real hardware using Bazzite Linux and a compatible ArtInChip / VSDISPLAY USB sensor display.

## Features

- Visual drag-and-drop dashboard editor
- CPU, GPU, RAM, storage and network monitoring
- Temperature and power sensors where supported by Linux and the hardware
- Gauges, charts and sparklines
- Custom backgrounds and themes
- Widget animations and alert triggers
- Multiple dashboard pages
- Light, dark and native system appearance
- German and English interface
- System tray integration
- Built-in diagnostics and compatibility checks
- Direct ArtInChip / VSDISPLAY USB output
- Standard monitor output for displays recognized by Linux

## Display support

OwnDash currently provides two display paths:

**Standard monitor output** works with HDMI, DisplayPort, USB-C and other displays that Linux recognizes as normal monitors.

**ArtInChip / VSDISPLAY USB output** provides direct USB support for compatible ArtInChip-based displays without requiring the display to appear as a normal Linux monitor.

Other proprietary USB-only displays may require a dedicated OwnDash backend for their protocol.

## Easy first start

### Required

Python knowledge is not required. OwnDash is provided as a self-contained AppImage.

### Optional — only for additional features


OwnDash Beta 2 is distributed as a self-contained **x86-64 AppImage**.

Download:

**`OwnDash-0.14.0-Beta-2-x86_64.AppImage`**

from the [OwnDash 0.14.0 Beta 2 release](https://github.com/x-Fuchur-x/owndash/releases/tag/v0.14.0-beta.2).

Make the AppImage executable if required by your Linux desktop and launch it by double-clicking it.

No manual Python or PySide6 installation is required.

On the first launch, OwnDash automatically opens its setup and compatibility assistant. It checks the computer and explains in plain language which features are available.

For compatible ArtInChip / VSDISPLAY devices, OwnDash can offer graphical installation of the required USB permission rule using the desktop's normal administrator authentication.

No privileged command is executed automatically at startup.

## Sensors and compatibility

OwnDash uses common Linux interfaces including `/proc`, `sysfs`, `hwmon`, DRM and `powercap` instead of targeting one specific Linux distribution.

Sensor availability depends on the kernel, driver and hardware. A missing optional sensor is **not an installation failure**.

For example, a GPU may expose utilization and temperature but not power consumption. OwnDash continues to work and simply marks that individual reading as unavailable.

Additional NVIDIA telemetry can be obtained through `nvidia-smi` when available.

OwnDash includes **Help → System and sensor information** to show the capabilities detected on the current computer.

## Tested platform

OwnDash 0.14.0 Beta 1 has been tested successfully on:

- Bazzite Linux
- KDE Plasma
- AMD CPU/GPU hardware
- x86-64
- Compatible ArtInChip / VSDISPLAY direct USB hardware
- Standard Linux monitor output

OwnDash is designed around common Linux interfaces and does **not** require Bazzite or KDE.

Other distributions, desktop environments and hardware configurations may work, but have not yet been tested to the same extent.

Testing and compatibility reports are welcome.

## Help and bug reports

OwnDash includes:

- **OwnDash Help** — getting started and FAQ
- **System check** — beginner-friendly compatibility overview
- **System and sensor information** — detailed detected capabilities
- **Report a bug** — prepares a GitHub issue with useful diagnostic information

Bugs and feature requests can also be reported through [GitHub Issues](https://github.com/x-Fuchur-x/owndash/issues).

## Developers / running from source

Python 3.11 or newer is required when running OwnDash from source.

From a virtual environment:

```bash
python -m pip install -e .
owndash
```

Core Python dependencies are declared in `pyproject.toml` and include PySide6, Pillow, PyUSB and cryptography.

The repository also contains the AppImage build tooling and GitHub Actions workflows used by the project.

## Beta status

OwnDash is currently beta software.

Bugs and compatibility issues are possible. Feedback from different Linux distributions, hardware configurations and display types is especially valuable during the beta period.

## License

OwnDash is released under the **MIT License**.

Third-party components and acknowledgements are documented in [`THIRD_PARTY.md`](THIRD_PARTY.md).

Copyright © 2026 **Markus Rosinski**