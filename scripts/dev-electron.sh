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

echo "Starting DroidLens Desktop (Node $(node -v))..."
exec npx concurrently -k \
  "npm run dev:backend" \
  "npm run dev:frontend" \
  "npx wait-on -t 60000 http-get://127.0.0.1:8765/health http://localhost:5173 && npx electron ."
