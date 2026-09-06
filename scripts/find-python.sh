#!/usr/bin/env bash
# Resolve the best Python 3.10+ interpreter for DroidLens (stdout = path).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

version_ok() {
  local exe="$1"
  "$exe" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

deps_ok() {
  local exe="$1"
  PYTHONPATH="$ROOT/backend" "$exe" - <<'PY' >/dev/null 2>&1
import fastapi
import uvicorn
import sqlalchemy
PY
}

collect_candidates() {
  local -a raw=()
  [[ -n "${DROIDLENS_PYTHON:-}" ]] && raw+=("$DROIDLENS_PYTHON")
  [[ -n "${INSPECTIQ_PYTHON:-}" ]] && raw+=("$INSPECTIQ_PYTHON")
  raw+=(
    python3.13 python3.12 python3.11 python3.10
    python3 python
    /usr/bin/python3 /usr/local/bin/python3
  )
  local c seen=""
  for c in "${raw[@]}"; do
    [[ -z "$c" ]] && continue
    if command -v "$c" >/dev/null 2>&1; then
      local resolved
      resolved="$(command -v "$c")"
      if ! echo "$seen" | grep -qx "$resolved"; then
        echo "$resolved"
        seen="${seen}${resolved}"$'\n'
      fi
    elif [[ -x "$c" ]]; then
      if ! echo "$seen" | grep -qx "$c"; then
        echo "$c"
        seen="${seen}${c}"$'\n'
      fi
    fi
  done
}

BEST=""
BEST_WITH_DEPS=""

while IFS= read -r exe; do
  [[ -z "$exe" ]] && continue
  if ! version_ok "$exe"; then
    continue
  fi
  BEST="${BEST:-$exe}"
  if deps_ok "$exe"; then
    BEST_WITH_DEPS="$exe"
    break
  fi
done < <(collect_candidates)

if [[ -n "$BEST_WITH_DEPS" ]]; then
  echo "$BEST_WITH_DEPS"
  exit 0
fi

if [[ -n "$BEST" ]]; then
  echo "$BEST"
  exit 0
fi

echo "DroidLens requires Python 3.10 or newer." >&2
echo "Install Python 3.12, then run: bash scripts/install-all.sh" >&2
echo "Or set DROIDLENS_PYTHON=/path/to/python3.12" >&2
exit 1
