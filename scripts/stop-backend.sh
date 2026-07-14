#!/usr/bin/env bash
# Stop any running DroidLens/InspectIQ backend on the default port.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/ensure-backend-port.sh"
