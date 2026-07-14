#!/usr/bin/env bash
# Install DroidLens .desktop launcher + icon for Linux (AppImage or extracted install).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="DroidLens"
DESKTOP_ID="droidlens.desktop"
ICON_SRC="$ROOT/assets/branding/icons/256x256.png"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"

usage() {
  cat <<EOF
Usage: $0 [--exec PATH]

Install a desktop launcher for DroidLens on Linux.

  --exec PATH   Path to DroidLens AppImage or binary (required if not in PATH)

Example:
  $0 --exec "$ROOT/dist-electron/DroidLens-1.0.0.AppImage"
EOF
}

EXEC=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --exec) EXEC="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$EXEC" ]]; then
  if command -v droidlens >/dev/null 2>&1; then
    EXEC="$(command -v droidlens)"
  else
    echo "Error: pass --exec /path/to/DroidLens.AppImage"
    exit 1
  fi
fi

if [[ ! -f "$EXEC" ]]; then
  echo "Error: executable not found: $EXEC"
  exit 1
fi

if [[ ! -f "$ICON_SRC" ]]; then
  echo "Generating icons..."
  (cd "$ROOT" && npm run generate:icons)
fi

mkdir -p "$DESKTOP_DIR" "$ICON_DIR"
cp "$ICON_SRC" "$ICON_DIR/droidlens.png"

cat > "$DESKTOP_DIR/$DESKTOP_ID" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Professional Android UI Inspector — See. Inspect. Automate.
Exec=${EXEC}
Icon=${ICON_DIR}/droidlens.png
Terminal=false
Categories=Development;Utility;
StartupWMClass=droidlens
EOF

chmod +x "$EXEC" 2>/dev/null || true
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "Installed: $DESKTOP_DIR/$DESKTOP_ID"
echo "Icon:      $ICON_DIR/droidlens.png"
echo "Launch DroidLens from your app menu or pin it to the dock."
