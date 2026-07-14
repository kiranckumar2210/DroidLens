#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DROIDLENS_MOCK="${DROIDLENS_MOCK:-${INSPECTIQ_MOCK:-true}}"
export PYTHONPATH="${ROOT}/backend"

echo "DroidLens — starting backend (mock=${DROIDLENS_MOCK})..."
cd "${ROOT}/backend"
python3 -m inspectiq.api.main &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 1

echo "DroidLens — starting frontend..."
cd "${ROOT}/frontend"
npm run dev
