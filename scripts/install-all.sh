#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/ensure-node.sh"

PYTHON=""
if [[ -f "$ROOT/scripts/find-python.cjs" ]] && command -v node >/dev/null 2>&1; then
  PYTHON="$(node "$ROOT/scripts/find-python.cjs")"
elif [[ -f "$ROOT/scripts/find-python.sh" ]]; then
  PYTHON="$(bash "$ROOT/scripts/find-python.sh")"
else
  echo "Missing Python resolver script" >&2
  exit 1
fi
export DROIDLENS_PYTHON="$PYTHON"
chmod +x "$ROOT/scripts/find-python.sh" 2>/dev/null || true

echo "Installing DroidLens dependencies (Node $(node -v), $("$PYTHON" --version 2>&1))..."

("$PYTHON" -m pip install -r backend/requirements.txt)
(cd frontend && npm install)
npm install
npm run generate:icons

echo ""
echo "Done. Python: $PYTHON ($("$PYTHON" --version 2>&1))"
echo "Run:  DROIDLENS_MOCK=false npm run dev:electron"
