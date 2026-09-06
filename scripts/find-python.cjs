#!/usr/bin/env node
/**
 * Resolve the best Python 3.10+ interpreter for DroidLens.
 * Prints absolute path/command to stdout; exits 1 on failure.
 */
const { spawnSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const ROOT = path.join(__dirname, '..')
const BACKEND = path.join(ROOT, 'backend')

function run(exe, args, opts = {}) {
  const shell = process.platform === 'win32' && /\s/.test(exe)
  return spawnSync(exe, args, {
    encoding: 'utf8',
    timeout: 15000,
    shell: shell || opts.shell,
    env: opts.env,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
}

function versionOk(exe) {
  const r = run(exe, ['-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'])
  return r.status === 0
}

function depsOk(exe) {
  const r = run(exe, ['-c', 'import fastapi, uvicorn, sqlalchemy'], {
    env: { ...process.env, PYTHONPATH: BACKEND },
  })
  return r.status === 0
}

function resolveExe(name) {
  if (path.isAbsolute(name) && fs.existsSync(name)) return name
  if (process.platform === 'win32') {
    const r = run('where', [name], { shell: true })
    if (r.status === 0 && r.stdout.trim()) {
      return r.stdout.trim().split(/\r?\n/)[0]
    }
    return name
  }
  const r = run('command', ['-v', name], { shell: true })
  if (r.status === 0 && r.stdout.trim()) return r.stdout.trim()
  return name
}

function collectCandidates() {
  const fromEnv = [process.env.DROIDLENS_PYTHON, process.env.INSPECTIQ_PYTHON, process.env.PYTHON].filter(Boolean)
  const names = process.platform === 'win32'
    ? ['py -3.13', 'py -3.12', 'py -3.11', 'py -3.10', 'py -3', 'python3', 'python']
    : ['python3.13', 'python3.12', 'python3.11', 'python3.10', 'python3', 'python', '/usr/local/bin/python3', '/usr/bin/python3']

  const seen = new Set()
  const out = []
  for (const raw of [...fromEnv, ...names]) {
    if (!raw || seen.has(raw)) continue
    seen.add(raw)
    if (raw.includes(' ') || path.isAbsolute(raw)) {
      out.push(raw)
    } else {
      out.push(resolveExe(raw))
    }
  }
  return out
}

let fallback = null
for (const exe of collectCandidates()) {
  if (!versionOk(exe)) continue
  fallback = fallback || exe
  if (depsOk(exe)) {
    process.stdout.write(`${exe}\n`)
    process.exit(0)
  }
}

if (fallback) {
  process.stdout.write(`${fallback}\n`)
  process.exit(0)
}

console.error('DroidLens requires Python 3.10 or newer.')
console.error('Install Python 3.12, then run: bash scripts/install-all.sh')
console.error('Or set DROIDLENS_PYTHON to your Python executable.')
process.exit(1)
