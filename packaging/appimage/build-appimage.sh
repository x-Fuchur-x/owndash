#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD="$ROOT/build/appimage"
VENV="$BUILD/venv"
APPDIR="$BUILD/OwnDash.AppDir"
PYI="$BUILD/pyinstaller"

rm -rf "$BUILD"
mkdir -p "$BUILD"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel setuptools
"$VENV/bin/python" -m pip install pyinstaller "$ROOT"

"$VENV/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name OwnDash \
  --distpath "$PYI" \
  --workpath "$BUILD/pyi-work" \
  --specpath "$BUILD" \
  --collect-all PySide6 \
  --collect-all usb \
  --collect-all cryptography \
  --add-data "$ROOT/src/owndash/assets:owndash/assets" \
  --add-data "$ROOT/src/owndash/resources:owndash/resources" \
  "$ROOT/src/owndash/__main__.py"

mkdir -p "$APPDIR/usr/bin/owndash"
mkdir -p "$APPDIR/usr/share/metainfo"

cp -a "$PYI/OwnDash/." "$APPDIR/usr/bin/owndash/"
cp "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"
cp "$ROOT/packaging/org.owndash.OwnDash.desktop" \
  "$APPDIR/org.owndash.OwnDash.desktop"

# AppStream metadata.
# appimagetool currently looks for the legacy .appdata.xml filename.
cp "$ROOT/packaging/org.owndash.OwnDash.metainfo.xml" \
  "$APPDIR/usr/share/metainfo/org.owndash.OwnDash.appdata.xml"

cp "$ROOT/src/owndash/assets/owndash.svg" \
  "$APPDIR/org.owndash.OwnDash.svg"
cp "$ROOT/src/owndash/assets/owndash.svg" \
  "$APPDIR/.DirIcon"

chmod +x "$APPDIR/AppRun"

APPIMAGETOOL="${APPIMAGETOOL:-$(command -v appimagetool || true)}"
if [[ -z "$APPIMAGETOOL" ]]; then
  echo "appimagetool not found. Set APPIMAGETOOL=/path/to/appimagetool." >&2
  exit 2
fi

VERSION="$(
  PYTHONPATH="$ROOT/src" \
    python3 -c 'from owndash import __version__; print(__version__.replace(" ", "-"))'
)"

OUT="$ROOT/dist/OwnDash-${VERSION}-x86_64.AppImage"
mkdir -p "$ROOT/dist"

ARCH=x86_64 \
APPIMAGE_EXTRACT_AND_RUN=1 \
  "$APPIMAGETOOL" "$APPDIR" "$OUT"

chmod +x "$OUT"

echo "$OUT"
