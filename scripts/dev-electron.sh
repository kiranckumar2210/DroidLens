#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/ensure-node.sh"

if [[ ! -x "$ROOT/node_modules/.bin/concurrently" ]]; then
  echo "Installing root dependencies..."
  npm install
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

export INSPECTIQ_MOCK="${INSPECTIQ_MOCK:-false}"
export DROIDLENS_MOCK="${DROIDLENS_MOCK:-false}"

if [[ -f "$ROOT/scripts/find-python.cjs" ]] && command -v node >/dev/null 2>&1; then
  export DROIDLENS_PYTHON="$(node "$ROOT/scripts/find-python.cjs")"
elif [[ -f "$ROOT/scripts/find-python.sh" ]]; then
  export DROIDLENS_PYTHON="$(bash "$ROOT/scripts/find-python.sh")"
fi
if [[ -n "${DROIDLENS_PYTHON:-}" ]]; then
  echo "Using Python: $($DROIDLENS_PYTHON --version 2>&1) ($DROIDLENS_PYTHON)"
fi

echo "Starting DroidLens Desktop (Node $(node -v))..."
exec npx concurrently -k \
  "npm run dev:backend" \
  "npm run dev:frontend" \
  "npx wait-on -t 120000 http-get://127.0.0.1:8765/health http://localhost:5173 && npx electron ."
