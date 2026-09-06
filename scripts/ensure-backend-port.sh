#!/usr/bin/env bash
# Free DroidLens backend port if a stale instance from a prior dev session is still running.
set -euo pipefail

PORT="${DROIDLENS_PORT:-${INSPECTIQ_PORT:-8765}}"

find_pids_on_port() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti ":${PORT}" 2>/dev/null || true
  elif command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep "127.0.0.1:${PORT}" | grep -oP 'pid=\K[0-9]+' || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser "${PORT}/tcp" 2>/dev/null | tr ' ' '\n' || true
  fi
}

find_droidlens_backend_pid() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -f "inspectiq\.api\.main" 2>/dev/null | head -1 || true
    return
  fi
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    local cmd
    cmd="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    if echo "$cmd" | grep -qE 'inspectiq\.api\.main'; then
      echo "$pid"
      return
    fi
  done < <(find_pids_on_port)
}

is_droidlens_backend_cmd() {
  echo "$1" | grep -qE 'inspectiq\.api\.main'
}

is_safe_dev_blocker_cmd() {
  # Common accidental dev servers on 8765 — safe to stop for DroidLens startup.
  echo "$1" | grep -qE 'python3? -m http\.server|SimpleHTTPRequestHandler|http\.server'
}

kill_pid() {
  local pid="$1"
  kill "$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.2
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  done
  kill -9 "$pid" 2>/dev/null || true
}

PIDS="$(find_pids_on_port | tr '\n' ' ' | xargs echo -n 2>/dev/null || true)"
[[ -z "${PIDS// /}" ]] && exit 0

FIRST_PID="$(echo "$PIDS" | awk '{print $1}')"
CMD="$(ps -p "$FIRST_PID" -o args= 2>/dev/null || true)"
DROIDLENS_PID="$(find_droidlens_backend_pid || true)"

if [[ -n "${DROIDLENS_PID:-}" ]] || is_droidlens_backend_cmd "${CMD:-}"; then
  KILL_PID="${DROIDLENS_PID:-$FIRST_PID}"
  echo "Stopping stale DroidLens backend on port ${PORT} (pid ${KILL_PID})..."
  kill_pid "$KILL_PID"
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    kill -9 "$pid" 2>/dev/null || true
  done < <(find_pids_on_port)
  echo "Port ${PORT} cleared."
  exit 0
fi

if is_safe_dev_blocker_cmd "${CMD:-}"; then
  echo "Port ${PORT} blocked by dev HTTP server (pid ${FIRST_PID}) — stopping it..."
  echo "  ${CMD}"
  kill_pid "$FIRST_PID"
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    kill -9 "$pid" 2>/dev/null || true
  done < <(find_pids_on_port)
  echo "Port ${PORT} cleared."
  exit 0
fi

echo "Port ${PORT} is already in use by another process (pid ${FIRST_PID}):"
echo "  ${CMD}"
echo ""
echo "Stop that process, or run with a different port:"
echo "  DROIDLENS_PORT=8766 npm run dev"
exit 1
