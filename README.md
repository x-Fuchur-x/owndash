# OwnDash

**Your display. Your design. — Linux hardware dashboards without the terminal headache.**

OwnDash is a visual dashboard editor for Linux PC displays. It is designed for people who want a useful, attractive hardware-monitoring display without having to understand Python, `hwmon`, USB protocols or Linux internals.

> **Beta software:** OwnDash is currently in public-beta preparation. The first real-hardware development and testing has been performed on Bazzite/KDE with AMD hardware. Testing on other Linux distributions, desktops and hardware is welcome.

## What OwnDash does

Create dashboards with CPU, GPU, memory, storage, network, temperature and power widgets; gauges and charts; custom backgrounds and animations; multiple dashboard pages; and live output to a PC case display or secondary monitor.

OwnDash supports two display paths:

- **Standard monitor output** — for HDMI, DisplayPort, USB-C and other displays Linux recognizes as normal monitors.
- **ArtInChip / VSDISPLAY USB output** — direct USB support for compatible ArtInChip devices.

Other proprietary USB-only displays may require a dedicated OwnDash backend for their protocol.

## Easy first start

On the first launch, OwnDash opens a **system check**. It explains in plain language whether the computer is ready and separates real requirements from optional sensor features. The check can be run again at any time from **Help → System check**.

A missing optional sensor is **not an installation failure**. For example, a GPU may expose utilization and temperature but not power consumption. OwnDash continues to work and simply marks that individual reading as unavailable.

## Requirements

For normal users, the goal is a self-contained Linux build so Python knowledge is not required.

### Required

- Linux on **x86-64** for the first binary release
- A graphical Linux session using **Wayland or X11**
- Standard Linux `/proc` and `/sys` interfaces

### Optional — only for additional features

- `hwmon` — hardware temperatures and other sensors when provided by the kernel/driver
- `powercap` / RAPL — CPU/package power on supported systems
- `nvidia-smi` — additional NVIDIA telemetry when supplied by the NVIDIA driver
- `lspci` — friendly GPU model names
- USB permission/udev rule — only for direct ArtInChip/VSDISPLAY USB access

OwnDash detects these capabilities at runtime. It does **not** require KDE or Bazzite.

## Linux and hardware compatibility

OwnDash uses common Linux interfaces such as `/proc`, `sysfs`, `hwmon`, DRM and `powercap` instead of hard-coding one Linux distribution. AMD and Intel GPU telemetry is discovered through Linux interfaces where available. NVIDIA telemetry can additionally use `nvidia-smi`.

Sensor availability always depends on the kernel, driver and hardware. OwnDash's **Help → System and sensor information** window shows exactly what the current computer provides, and the same capability report is included automatically when preparing a bug report.

## Installation

### End users

The public beta is prepared around a self-contained **x86-64 AppImage**. The repository contains a reproducible AppImage build script and GitHub Actions workflow. Until a GitHub Release publishes the built AppImage, source archives remain primarily for developers and testers.

### Developers / running from source

Requires Python 3.11 or newer. From a virtual environment, install the project dependencies and run:

```bash
python -m pip install -e .
owndash
```

Core Python dependencies are declared in `pyproject.toml`: PySide6, Pillow, PyUSB and cryptography.

## ArtInChip / VSDISPLAY USB access

Compatible ArtInChip USB displays require permission for OwnDash to access the USB device. A udev rule is included in:

```text
src/owndash/packaging/99-owndash-usb.rules
```

The future end-user installer/package should install this rule automatically. Until then, source-based testers may need to install it manually according to their distribution's udev setup.

OwnDash also refuses to take over the supported USB display while the legacy `tinyscreen.service` is active, preventing two applications from controlling the same device.

## Help and troubleshooting

OwnDash includes:

- **OwnDash Help** — getting started and FAQ
- **System check** — beginner-friendly compatibility overview
- **System and sensor information** — detailed detected capabilities
- **Report a bug** — opens a prepared GitHub issue with useful system/sensor diagnostics
- **OwnDash on GitHub** — project page

## Project status

OwnDash is MIT-licensed beta software by **Markus Rosinski**. See `THIRD_PARTY.md` for third-party acknowledgements and licenses.

Project page: `https://github.com/x-Fuchur-x/owndash`


## Release packaging

The repository includes `packaging/appimage/build-appimage.sh` and a GitHub Actions AppImage workflow. The first-run system check also detects compatible ArtInChip/VSDISPLAY hardware and can offer a graphical USB-permission setup using the desktop's normal administrator authentication. No privileged command runs automatically.
