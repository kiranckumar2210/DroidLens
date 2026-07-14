#!/usr/bin/env node
/** Run a Python script with python/python3 depending on platform (CI + local). */
const { spawnSync } = require('child_process')

const args = process.argv.slice(2)
if (args.length === 0) {
  console.error('Usage: node scripts/run-python.cjs <script.py> [args...]')
  process.exit(1)
}

const candidates = [
  process.env.PYTHON,
  process.env.DROIDLENS_PYTHON,
  process.platform === 'win32' ? 'python' : 'python3',
  'python',
].filter(Boolean)

let lastError = null
for (const cmd of [...new Set(candidates)]) {
  const result = spawnSync(cmd, args, { stdio: 'inherit', shell: process.platform === 'win32' })
  if (result.error?.code === 'ENOENT') {
    lastError = result.error
    continue
  }
  process.exit(result.status ?? 1)
}

console.error('No Python interpreter found. Tried:', candidates.join(', '))
if (lastError) console.error(lastError.message)
process.exit(1)
