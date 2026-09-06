#!/usr/bin/env bash
# Start the DroidLens FastAPI backend (installs Python deps if needed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${DROIDLENS_PORT:-${INSPECTIQ_PORT:-8765}}"

if [[ -f "$ROOT/scripts/find-python.cjs" ]] && command -v node >/dev/null 2>&1; then
  PYTHON="$(node "$ROOT/scripts/find-python.cjs")"
elif [[ -f "$ROOT/scripts/find-python.sh" ]]; then
  PYTHON="$(bash "$ROOT/scripts/find-python.sh")"
else
  echo "Missing scripts/find-python.cjs or find-python.sh" >&2
  exit 1
fi
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
