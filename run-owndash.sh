#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

mkdir -p "$APP_DIR" "$ICON_DIR"
DESKTOP_FILE="$APP_DIR/org.owndash.OwnDash.desktop"
install -m 0644 "$ROOT/packaging/org.owndash.OwnDash.desktop" "$DESKTOP_FILE"
# During source-tree testing the packaged `owndash` console script is not installed.
# Point the per-user desktop entry at this launcher so KDE can resolve the exact
# desktop file/app-id and therefore use the same icon as the Qt window.
sed -i "s|^Exec=.*$|Exec=$ROOT/run-owndash.sh|" "$DESKTOP_FILE"
rm -f "$ICON_DIR/owndash.svg"
install -m 0644 "$ROOT/src/owndash/assets/owndash.svg" "$ICON_DIR/org.owndash.OwnDash.svg"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" >/dev/null 2>&1 || true
command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m owndash "$@"
