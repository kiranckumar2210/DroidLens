#!/usr/bin/env bash
# Start the DroidLens FastAPI backend (installs Python deps if needed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${DROIDLENS_PORT:-${INSPECTIQ_PORT:-8765}}"

echo "Checking Python dependencies..."
python3 -m pip install -q -r "$ROOT/backend/requirements.txt"

bash "$ROOT/scripts/ensure-backend-port.sh"

echo "Starting DroidLens backend on http://127.0.0.1:${PORT} ..."
cd "$ROOT/backend"
export PYTHONPATH=.
exec python3 -m inspectiq.api.main
