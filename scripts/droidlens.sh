#!/usr/bin/env bash
# DroidLens CLI wrapper for CI pipelines
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/backend"
exec python3 -m inspectiq.cli "$@"
