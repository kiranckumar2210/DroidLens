#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/ensure-node.sh"

PYTHON="$("$ROOT/scripts/find-python.sh")"
export DROIDLENS_PYTHON="$PYTHON"

echo "Installing DroidLens dependencies (Node $(node -v), $("$PYTHON" --version 2>&1))..."

("$PYTHON" -m pip install -r backend/requirements.txt)
(cd frontend && npm install)
npm install

echo ""
echo "Done. Python: $PYTHON ($("$PYTHON" --version 2>&1))"
echo "Run:  DROIDLENS_MOCK=false npm run dev:electron"
