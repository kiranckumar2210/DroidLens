const { app, BrowserWindow, shell, dialog, Menu, nativeImage, ipcMain } = require('electron')
const { spawn, spawnSync } = require('child_process')
const path = require('path')
const fs = require('fs')
const http = require('http')

const pkg = require('../package.json')

const APP_NAME = 'DroidLens'
const APP_TAGLINE = 'See. Inspect. Automate.'
const APP_VERSION = pkg.version || '1.0.0'

const BACKEND_PORT = process.env.DROIDLENS_PORT || process.env.INSPECTIQ_PORT || '8765'
const BACKEND_HOST = '127.0.0.1'
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`
const IS_DEV = !app.isPackaged

let mainWindow = null
let splashWindow = null
let backendProcess = null
let backendSpawnedByElectron = false
let backendStderrTail = ''

function assetPath(...parts) {
  return path.join(__dirname, '..', 'assets', 'branding', ...parts)
}

function getAppIcon() {
  const iconPath = assetPath('icon.png')
  if (fs.existsSync(iconPath)) {
    return nativeImage.createFromPath(iconPath)
  }
  return undefined
}

function isBackendExternal() {
  return IS_DEV || process.env.DROIDLENS_EXTERNAL_BACKEND === '1' || process.env.INSPECTIQ_EXTERNAL_BACKEND === '1'
}

function loadDesktopConfig() {
  const candidates = [
    path.join(app.getPath('userData'), 'desktop-config.json'),
    path.join(__dirname, 'desktop-config.json'),
  ]
  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate)) {
        return JSON.parse(fs.readFileSync(candidate, 'utf8'))
      }
    } catch (err) {
      console.warn('[electron] Failed to read desktop config:', candidate, err.message)
    }
  }
  return {}
}

function cloudApiUrlFromConfig() {
  const cfg = loadDesktopConfig()
  const raw = cfg.cloudApiUrl || cfg.authApiUrl || process.env.DROIDLENS_CLOUD_API_URL || ''
  return String(raw).trim().replace(/\/$/, '')
}

function startBackend() {
  return new Promise((resolve, reject) => {
    if (isBackendExternal()) {
      waitForBackend(120, 500)
        .then(() => {
          console.log('[electron] Using existing backend at', BACKEND_URL)
          resolve()
        })
        .catch(reject)
      return
    }

    let startupPending = true

    try {
      const backendDir = getBackendDir()
      const python = getPythonCommand()
      ensureBackendDeps(python, backendDir)
      const cloudApiUrl = cloudApiUrlFromConfig()

      const env = {
        ...process.env,
        PYTHONPATH: backendDir,
        DROIDLENS_PYTHON: python,
        DROIDLENS_MOCK: process.env.DROIDLENS_MOCK || process.env.INSPECTIQ_MOCK || 'false',
        DROIDLENS_PORT: BACKEND_PORT,
        INSPECTIQ_MOCK: process.env.DROIDLENS_MOCK || process.env.INSPECTIQ_MOCK || 'false',
        INSPECTIQ_PORT: BACKEND_PORT,
      }
      if (cloudApiUrl) {
        env.DROIDLENS_CLOUD_AUTH_URL = cloudApiUrl
        console.log('[electron] Cloud auth API:', cloudApiUrl)
      }

      const staticDir = getStaticDir()
      env.DROIDLENS_STATIC_DIR = staticDir
      console.log('[electron] Python:', python)
      console.log('[electron] Serving frontend from', staticDir)

      backendProcess = spawn(
        python,
        ['-m', 'inspectiq.api.main'],
        {
          cwd: backendDir,
          env,
          stdio: ['ignore', 'pipe', 'pipe'],
          shell: process.platform === 'win32' && /\s/.test(python),
        }
      )
      backendSpawnedByElectron = true

      backendProcess.stdout.on('data', (data) => {
        console.log(`[backend] ${data.toString().trim()}`)
      })

      backendProcess.stderr.on('data', (data) => {
        const text = data.toString()
        backendStderrTail = (backendStderrTail + text).slice(-4000)
        console.error(`[backend] ${text.trim()}`)
      })

      backendProcess.on('error', (err) => {
        startupPending = false
        reject(new Error(`Failed to start Python backend (${python}): ${err.message}`))
      })

      backendProcess.on('exit', (code) => {
        if (startupPending && code !== 0 && code !== null) {
          startupPending = false
          const detail = backendStderrTail.trim()
          reject(new Error(
            `Backend exited with code ${code} before becoming ready.${detail ? `\n\nBackend output:\n${detail.slice(-1200)}` : ''}`
          ))
          return
        }
        if (code !== 0 && code !== null) {
          console.error(`Backend exited with code ${code}`)
          if (backendStderrTail) {
            console.error('[backend stderr tail]', backendStderrTail.trim())
          }
        }
        backendProcess = null
      })

      waitForBackend(120, 500).then(() => {
        startupPending = false
        resolve()
      }).catch((err) => {
        startupPending = false
        const detail = backendStderrTail.trim()
        if (detail) {
          reject(new Error(`${err.message}\n\nBackend output:\n${detail.slice(-1200)}`))
        } else {
          reject(err)
        }
      })
    } catch (err) {
      startupPending = false
      reject(err instanceof Error ? err : new Error(String(err)))
    }
  })
}

function getStaticDir() {
  const distPath = path.join(__dirname, '..', 'frontend', 'dist')
  // Python backend cannot read inside app.asar — use asar-unpacked copy when packaged.
  if (!IS_DEV && distPath.includes(`${path.sep}app.asar${path.sep}`)) {
    const unpacked = distPath.replace(
      `${path.sep}app.asar${path.sep}`,
      `${path.sep}app.asar.unpacked${path.sep}`
    )
    if (fs.existsSync(unpacked)) {
      return unpacked
    }
  }
  return distPath
}

function getBackendDir() {
  if (IS_DEV) {
    return path.join(__dirname, '..', 'backend')
  }
  return path.join(process.resourcesPath, 'backend')
}

function versionOk(exe) {
  try {
    const r = spawnSync(exe, ['-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'], {
      encoding: 'utf8',
      timeout: 8000,
      shell: process.platform === 'win32' && /\s/.test(exe),
    })
    return r.status === 0
  } catch {
    return false
  }
}

function depsOk(exe, backendDir) {
  try {
    const r = spawnSync(exe, ['-c', 'import fastapi, uvicorn, sqlalchemy'], {
      env: { ...process.env, PYTHONPATH: backendDir },
      encoding: 'utf8',
      timeout: 15000,
      shell: process.platform === 'win32' && /\s/.test(exe),
    })
    return r.status === 0
  } catch {
    return false
  }
}

function resolvePythonCandidates() {
  const fromEnv = [process.env.DROIDLENS_PYTHON, process.env.INSPECTIQ_PYTHON].filter(Boolean)
  const names = process.platform === 'win32'
    ? ['py -3.13', 'py -3.12', 'py -3.11', 'py -3.10', 'py -3', 'python3', 'python']
    : ['python3.13', 'python3.12', 'python3.11', 'python3.10', 'python3', 'python']
  const seen = new Set()
  const out = []
  for (const c of [...fromEnv, ...names]) {
    if (!c || seen.has(c)) continue
    seen.add(c)
    out.push(c)
  }
  return out
}

function getPythonCommand() {
  if (process.env.DROIDLENS_PYTHON || process.env.INSPECTIQ_PYTHON) {
    return process.env.DROIDLENS_PYTHON || process.env.INSPECTIQ_PYTHON
  }

  const scriptCandidates = [
    path.join(__dirname, '..', 'scripts', 'find-python.cjs'),
    path.join(process.resourcesPath || '', 'app.asar', 'scripts', 'find-python.cjs'),
    path.join(process.resourcesPath || '', 'scripts', 'find-python.cjs'),
    path.join(__dirname, '..', 'scripts', 'find-python.sh'),
  ]
  for (const script of scriptCandidates) {
    if (!script || !fs.existsSync(script)) continue
    try {
      const cmd = script.endsWith('.cjs')
        ? ['node', [script]]
        : ['bash', [script]]
      const r = spawnSync(cmd[0], cmd[1], { encoding: 'utf8', timeout: 20000 })
      if (r.status === 0 && r.stdout.trim()) {
        return r.stdout.trim()
      }
    } catch {
      /* fall through */
    }
  }

  const backendDir = getBackendDir()
  let fallback = null
  for (const exe of resolvePythonCandidates()) {
    if (!versionOk(exe)) continue
    fallback = fallback || exe
    if (depsOk(exe, backendDir)) return exe
  }
  if (fallback) return fallback
  return process.platform === 'win32' ? 'python' : 'python3'
}

function ensureBackendDeps(python, backendDir) {
  if (depsOk(python, backendDir)) return
  const req = path.join(backendDir, 'requirements.txt')
  if (!fs.existsSync(req)) {
    throw new Error(`Missing ${req}`)
  }
  console.log('[electron] Installing Python backend dependencies (first launch may take a minute)...')
  const r = spawnSync(python, ['-m', 'pip', 'install', '-r', req], {
    cwd: backendDir,
    stdio: 'inherit',
    timeout: 300000,
    shell: process.platform === 'win32' && /\s/.test(python),
  })
  if (r.status !== 0) {
    throw new Error(
      `Failed to install Python dependencies.\nRun manually:\n  ${python} -m pip install -r backend/requirements.txt`
    )
  }
}

function waitForBackend(maxAttempts, intervalMs) {
  return new Promise((resolve, reject) => {
    let attempts = 0

    const check = () => {
      const req = http.get(`${BACKEND_URL}/health`, (res) => {
        if (res.statusCode === 200) {
          resolve()
        } else {
          retry()
        }
      })
      req.on('error', retry)
      req.setTimeout(2000, () => {
        req.destroy()
        retry()
      })
    }

    const retry = () => {
      attempts += 1
      if (attempts >= maxAttempts) {
        reject(new Error(
          `Backend failed to start within timeout (${Math.round(maxAttempts * intervalMs / 1000)}s) at ${BACKEND_URL}/health`
        ))
        return
      }
      setTimeout(check, intervalMs)
    }

    check()
  })
}

function stopBackend() {
  if (backendProcess && backendSpawnedByElectron) {
    backendProcess.kill('SIGTERM')
    backendProcess = null
    backendSpawnedByElectron = false
  }
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 420,
    height: 320,
    frame: false,
    transparent: false,
    resizable: false,
    center: true,
    alwaysOnTop: true,
    backgroundColor: '#263238',
    icon: getAppIcon(),
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  const splashHtml = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family:Segoe UI,system-ui,sans-serif;
    background:#263238;color:#eceff1;
    height:100vh;display:flex;flex-direction:column;
    align-items:center;justify-content:center;gap:16px;
  }
  img { width:96px;height:96px; }
  h1 { font-size:28px;font-weight:700;letter-spacing:-0.02em; }
  h1 span { color:#34A853; }
  p { color:#90a4ae;font-size:13px;letter-spacing:0.06em; }
  .bar { width:180px;height:4px;background:#37474f;border-radius:2px;overflow:hidden;margin-top:8px; }
  .bar i { display:block;height:100%;width:40%;background:linear-gradient(90deg,#34A853,#1E88E5);
    animation:slide 1.2s ease-in-out infinite; }
  @keyframes slide { 0%{transform:translateX(-100%)} 100%{transform:translateX(350%)} }
</style></head><body>
  <img src="file://${assetPath('icon.png').replace(/\\/g, '/')}" alt="" />
  <h1>Droid<span>Lens</span></h1>
  <p>${APP_TAGLINE}</p>
  <div class="bar"><i></i></div>
</body></html>`

  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(splashHtml)}`)
  splashWindow.once('ready-to-show', () => splashWindow.show())
}

function closeSplashWindow() {
  if (splashWindow) {
    splashWindow.close()
    splashWindow = null
  }
}

function createWindow() {
  const cloudApiUrl = cloudApiUrlFromConfig()
  const extraArgs = cloudApiUrl ? [`--cloud-api-url=${cloudApiUrl}`] : []

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: APP_NAME,
    icon: getAppIcon(),
    backgroundColor: '#0d1117',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      additionalArguments: extraArgs,
    },
    show: false,
  })

  mainWindow.once('ready-to-show', () => {
    closeSplashWindow()
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (IS_DEV) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadURL(`${BACKEND_URL}/`)
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function showAboutDialog() {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: `About ${APP_NAME}`,
    message: APP_NAME,
    detail: [
      APP_TAGLINE,
      '',
      'Professional Android UI inspection and automation platform.',
      'Inspect live devices, offline XML dumps, and generate production-ready locators.',
      '',
      `Version ${APP_VERSION}`,
      '© DroidLens',
    ].join('\n'),
    icon: getAppIcon(),
  })
}

function buildAppMenu() {
  const template = [
    ...(process.platform === 'darwin' ? [{
      label: APP_NAME,
      submenu: [
        { label: `About ${APP_NAME}`, click: showAboutDialog },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    }] : []),
    {
      label: 'Help',
      submenu: [
        { label: `About ${APP_NAME}`, click: showAboutDialog },
        {
          label: 'API Documentation',
          click: () => shell.openExternal(`${BACKEND_URL}/docs`),
        },
      ],
    },
  ]
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

function stripExt(name) {
  const i = name.lastIndexOf('.')
  return i > 0 ? name.slice(0, i) : name
}

function isXmlName(name) {
  const lower = name.toLowerCase()
  return lower.endsWith('.xml') || lower.endsWith('.uix')
}

function isImageName(name) {
  const lower = name.toLowerCase()
  return lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')
}

function scanFolderForPairs(folderPath) {
  const entries = fs.readdirSync(folderPath)
  return entries
    .filter(isXmlName)
    .map((xmlName) => {
      const base = stripExt(xmlName)
      const pngName = entries.find(
        (e) => isImageName(e) && stripExt(e).toLowerCase() === base.toLowerCase(),
      )
      return {
        label: base,
        xmlPath: path.join(folderPath, xmlName),
        screenshotPath: pngName ? path.join(folderPath, pngName) : null,
      }
    })
}

function registerXmlPackageIpc() {
  ipcMain.handle('pick-export-folder', async () => {
    const result = await dialog.showOpenDialog({
      title: 'Choose export folder',
      properties: ['openDirectory', 'createDirectory'],
    })
    if (result.canceled || !result.filePaths.length) return null
    return result.filePaths[0]
  })

  ipcMain.handle('pick-import-folder', async () => {
    const result = await dialog.showOpenDialog({
      title: 'Open folder with XML and PNG pairs',
      properties: ['openDirectory'],
    })
    if (result.canceled || !result.filePaths.length) return null
    return result.filePaths[0]
  })

  ipcMain.handle('export-xml-package', async (_event, payload) => {
    const { parentDir, folderName, baseName, xml, screenshotBase64, metadata } = payload
    const outDir = path.join(parentDir, folderName)
    fs.mkdirSync(outDir, { recursive: true })
    fs.writeFileSync(path.join(outDir, `${baseName}.xml`), xml, 'utf8')
    fs.writeFileSync(path.join(outDir, `${baseName}.png`), Buffer.from(screenshotBase64, 'base64'))
    if (metadata) {
      fs.writeFileSync(path.join(outDir, 'metadata.json'), JSON.stringify(metadata, null, 2), 'utf8')
    }
    return outDir
  })

  ipcMain.handle('read-folder-pairs', async (_event, folderPath) => {
    if (!folderPath || !fs.existsSync(folderPath)) return []
    return scanFolderForPairs(folderPath)
  })

  ipcMain.handle('read-package-paths', async (_event, { xmlPath, screenshotPath }) => {
    if (!xmlPath || !fs.existsSync(xmlPath)) {
      throw new Error(`XML file not found: ${xmlPath}`)
    }
    const xml = fs.readFileSync(xmlPath, 'utf8')
    let screenshotBase64 = null
    if (screenshotPath && fs.existsSync(screenshotPath)) {
      screenshotBase64 = fs.readFileSync(screenshotPath).toString('base64')
    }
    return { xml, screenshotBase64, xmlPath, screenshotPath: screenshotPath || null }
  })
}

async function bootstrap() {
  createSplashWindow()
  buildAppMenu()
  try {
    await startBackend()
    createWindow()
  } catch (err) {
    closeSplashWindow()
    dialog.showErrorBox(
      `${APP_NAME} Startup Error`,
      `${err.message}\n\nEnsure Python 3.10+ is installed with backend dependencies:\n  bash scripts/install-all.sh\n\nOr set DROIDLENS_PYTHON to your Python 3.12 path.`
    )
    app.quit()
  }
}

app.setName(APP_NAME)
if (process.platform === 'win32') {
  app.setAppUserModelId('com.droidlens.desktop')
}

app.whenReady().then(() => {
  registerXmlPackageIpc()
  return bootstrap()
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    bootstrap()
  }
})

app.on('before-quit', () => {
  stopBackend()
})

process.on('SIGTERM', () => {
  stopBackend()
  app.quit()
})
