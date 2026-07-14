#!/usr/bin/env bash
# Free DroidLens backend port if a stale instance from a prior dev session is still running.
set -euo pipefail

PORT="${DROIDLENS_PORT:-${INSPECTIQ_PORT:-8765}}"

find_pids_on_port() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti ":${PORT}" 2>/dev/null || true
  elif command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep "127.0.0.1:${PORT}" | grep -oP 'pid=\K[0-9]+' || true
  fi
}

find_uvicorn_pid() {
  # Match parent uvicorn regardless of which worker pid lsof returns first.
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -f "uvicorn inspectiq.api.main:app.*--port ${PORT}" 2>/dev/null | head -1 || true
    return
  fi
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    local cmd
    cmd="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    if echo "$cmd" | grep -qE 'uvicorn inspectiq\.api\.main'; then
      echo "$pid"
      return
    fi
  done < <(find_pids_on_port)
}

PIDS="$(find_pids_on_port | tr '\n' ' ' | xargs echo -n 2>/dev/null || true)"
[[ -z "${PIDS// /}" ]] && exit 0

UVICORN_PID="$(find_uvicorn_pid || true)"

if [[ -n "${UVICORN_PID:-}" ]]; then
  echo "Stopping stale DroidLens backend on port ${PORT} (pid ${UVICORN_PID})..."
  kill "$UVICORN_PID" 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.2
    [[ -z "$(find_pids_on_port | head -1 || true)" ]] && exit 0
  done
  # Force-kill anything still bound to the port
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    kill -9 "$pid" 2>/dev/null || true
  done < <(find_pids_on_port)
  echo "Port ${PORT} cleared."
  exit 0
fi

# Non-DroidLens process owns the port
FIRST_PID="$(echo "$PIDS" | awk '{print $1}')"
CMD="$(ps -p "$FIRST_PID" -o args= 2>/dev/null || true)"
echo "Port ${PORT} is already in use by another process (pid ${FIRST_PID}):"
echo "  ${CMD}"
echo ""
echo "Stop that process, or run with a different port:"
echo "  DROIDLENS_PORT=8766 npm run dev"
exit 1
