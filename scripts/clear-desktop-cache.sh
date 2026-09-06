#!/usr/bin/env bash
# Clear DroidLens Electron cache (fixes stale v1.0 UI after upgrading to v2.0).
set -euo pipefail

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/DroidLens"

echo "Stopping DroidLens if running..."
pkill -f 'DroidLens' 2>/dev/null || true
pkill -f 'droidlens' 2>/dev/null || true
sleep 1

if [[ -d "$CONFIG_DIR" ]]; then
  echo "Clearing cache in $CONFIG_DIR ..."
  rm -rf \
    "$CONFIG_DIR/Cache" \
    "$CONFIG_DIR/Code Cache" \
    "$CONFIG_DIR/GPUCache" \
    "$CONFIG_DIR/DawnGraphiteCache" \
    "$CONFIG_DIR/DawnWebGPUCache" \
    "$CONFIG_DIR/Service Worker" \
    "$CONFIG_DIR/Session Storage" \
    "$CONFIG_DIR/blob_storage"
  echo "Done. Relaunch DroidLens 2.0.0 AppImage or deb."
else
  echo "No config dir at $CONFIG_DIR — nothing to clear."
fi
