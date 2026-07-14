#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "$ROOT/scripts/ensure-node.sh"

echo "Installing DroidLens dependencies (Node $(node -v))..."

(cd backend && python3 -m pip install -r requirements.txt)
(cd frontend && npm install)
npm install

echo ""
echo "Done. Run:  npm run dev:electron"
