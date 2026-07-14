#!/usr/bin/env bash
# Launch DroidLens Desktop with cloud auth (Railway) + local ADB backend.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env.desktop" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env.desktop"
  set +a
fi

if [[ -z "${DROIDLENS_CLOUD_API_URL:-}" ]]; then
  echo "Set DROIDLENS_CLOUD_API_URL in .env.desktop (see .env.desktop.example)"
  exit 1
fi

if [[ -z "${DROIDLENS_JWT_SECRET:-}" ]]; then
  echo "Warning: DROIDLENS_JWT_SECRET is not set — cloud login tokens may not work locally."
fi

export DROIDLENS_MOCK=false
export DROIDLENS_CLOUD_AUTH_URL="$DROIDLENS_CLOUD_API_URL"

if [[ ! -f "$ROOT/electron/desktop-config.json" ]]; then
  mkdir -p "$ROOT/electron"
  printf '{"cloudApiUrl":"%s"}\n' "$DROIDLENS_CLOUD_API_URL" > "$ROOT/electron/desktop-config.json"
fi

exec bash "$ROOT/scripts/dev-electron.sh"
