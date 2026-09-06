#!/usr/bin/env bash
# Start the DroidLens FastAPI backend (installs Python deps if needed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${DROIDLENS_PORT:-${INSPECTIQ_PORT:-8765}}"

PYTHON="$("$ROOT/scripts/find-python.sh")"
export DROIDLENS_PYTHON="$PYTHON"

echo "Using Python: $("$PYTHON" --version 2>&1) ($PYTHON)"

echo "Checking Python dependencies..."
if ! PYTHONPATH="$ROOT/backend" "$PYTHON" -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
  echo "Installing backend requirements (first run may take a minute)..."
  "$PYTHON" -m pip install -r "$ROOT/backend/requirements.txt"
else
  "$PYTHON" -m pip install -q -r "$ROOT/backend/requirements.txt"
fi

bash "$ROOT/scripts/ensure-backend-port.sh"

echo "Starting DroidLens backend on http://127.0.0.1:${PORT} ..."
cd "$ROOT/backend"
export PYTHONPATH=.
exec "$PYTHON" -m inspectiq.api.main
