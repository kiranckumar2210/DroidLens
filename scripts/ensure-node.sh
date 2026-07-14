#!/usr/bin/env bash
# Ensure Node.js 18+ via nvm when system node is too old.
set -euo pipefail

MIN_NODE_MAJOR=18

current_major() {
  node -p "process.versions.node.split('.')[0]" 2>/dev/null || echo "0"
}

load_nvm() {
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  if [[ -s "$NVM_DIR/nvm.sh" ]]; then
    # shellcheck disable=SC1090
    source "$NVM_DIR/nvm.sh"
    return 0
  fi
  return 1
}

ensure_node() {
  local major
  major="$(current_major)"
  if [[ "$major" -ge "$MIN_NODE_MAJOR" ]]; then
    return 0
  fi

  echo "DroidLens requires Node.js >= ${MIN_NODE_MAJOR} (found: $(node -v 2>/dev/null || echo 'none'))"

  if load_nvm; then
    if [[ -f .nvmrc ]]; then
      nvm install
      nvm use
    else
      nvm install 20
      nvm use 20
    fi
    major="$(current_major)"
    if [[ "$major" -ge "$MIN_NODE_MAJOR" ]]; then
      echo "Using Node $(node -v) via nvm"
      return 0
    fi
  fi

  echo ""
  echo "Install Node.js 18+ and retry:"
  echo "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
  echo "  nvm install 20 && nvm use 20"
  exit 1
}

ensure_node
