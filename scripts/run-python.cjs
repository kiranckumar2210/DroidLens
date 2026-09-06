#!/usr/bin/env node
/** Run a Python module/script using the DroidLens Python resolver. */
const { spawnSync } = require('child_process')
const path = require('path')
const fs = require('fs')

const args = process.argv.slice(2)
if (args.length === 0) {
  console.error('Usage: node scripts/run-python.cjs <script.py|-m module> [args...]')
  process.exit(1)
}

function resolvePython() {
  if (process.env.DROIDLENS_PYTHON) return process.env.DROIDLENS_PYTHON
  const root = path.join(__dirname, '..')
  const cjs = path.join(root, 'scripts', 'find-python.cjs')
  const sh = path.join(root, 'scripts', 'find-python.sh')
  if (fs.existsSync(cjs)) {
    const r = spawnSync('node', [cjs], { encoding: 'utf8' })
    if (r.status === 0 && r.stdout.trim()) return r.stdout.trim()
  }
  if (fs.existsSync(sh)) {
    const r = spawnSync('bash', [sh], { encoding: 'utf8' })
    if (r.status === 0 && r.stdout.trim()) return r.stdout.trim()
  }
  return process.platform === 'win32' ? 'python' : 'python3'
}

const python = resolvePython()
const shell = process.platform === 'win32' && /\s/.test(python)
const result = spawnSync(python, args, { stdio: 'inherit', shell })
if (result.error?.code === 'ENOENT') {
  console.error(`Python interpreter not found: ${python}`)
  process.exit(1)
}
process.exit(result.status ?? 1)
