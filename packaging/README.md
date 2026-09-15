# OwnDash packaging

Normal users should not need Python, pip or terminal commands.

## Intended release artifact

The primary public-beta download is an **x86-64 AppImage** containing OwnDash and
its Python runtime dependencies. The AppImage remains unprivileged.

Direct ArtInChip/VSDISPLAY USB access needs a udev rule. OwnDash detects this at
first run and, after an explicit click on **Set up USB access**, uses `pkexec` to
show the desktop's normal administrator-authentication dialog and install:

`/etc/udev/rules.d/99-owndash-usb.rules`

No privileged command runs automatically.

## Official AppImage compatibility baseline

Official OwnDash release AppImages are built on **Debian 12** to provide a
conservative Linux compatibility baseline.

The release workflow verifies that bundled ELF binaries do not require a GLIBC
version newer than **GLIBC 2.36**.

After the build, the finished AppImage is launched in a clean Debian 12
environment as an automated compatibility smoke test. This verifies that the
packaged application can start on the release baseline.

This compatibility baseline does not guarantee that every Linux distribution
with GLIBC 2.36 provides the same hardware drivers, sensors, desktop integration
or optional system libraries.

## Build

`packaging/appimage/build-appimage.sh`

The script expects `appimagetool` in PATH (or
`APPIMAGETOOL=/path/to/appimagetool`) and installs the Python build dependencies
into a temporary virtual environment.

A local build uses the developer system's available Python and system environment
and therefore is **not automatically equivalent to an official release build**.

Official release AppImages are built through `.github/workflows/appimage.yml`,
which uses the Debian 12 compatibility baseline, verifies the maximum required
GLIBC version and performs the Debian 12 smoke test.
