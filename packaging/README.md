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

## Build

`packaging/appimage/build-appimage.sh`

The script expects `appimagetool` in PATH (or `APPIMAGETOOL=/path/to/appimagetool`)
and installs the Python build dependencies into a temporary virtual environment.

GitHub Actions can build the AppImage using `.github/workflows/appimage.yml`.
