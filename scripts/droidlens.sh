#!/usr/bin/env bash
# DroidLens CLI wrapper for CI pipelines
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/backend"
if [[ -f "$ROOT/scripts/find-python.cjs" ]] && command -v node >/dev/null 2>&1; then
  PYTHON="$(node "$ROOT/scripts/find-python.cjs")"
else
  PYTHON="$(bash "$ROOT/scripts/find-python.sh")"
fi
exec "$PYTHON" -m inspectiq.cli "$@"
