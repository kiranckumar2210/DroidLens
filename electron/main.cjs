const { app, BrowserWindow, shell, dialog, Menu, nativeImage } = require('electron')
const { spawn } = require('child_process')
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

function startBackend() {
  return new Promise((resolve, reject) => {
    if (isBackendExternal()) {
      waitForBackend(60, 500)
        .then(() => {
          console.log('[electron] Using existing backend at', BACKEND_URL)
          resolve()
        })
        .catch(reject)
      return
    }

    const backendDir = getBackendDir()
    const python = getPythonCommand()

    const env = {
      ...process.env,
      PYTHONPATH: backendDir,
      DROIDLENS_MOCK: process.env.DROIDLENS_MOCK || process.env.INSPECTIQ_MOCK || 'false',
      DROIDLENS_PORT: BACKEND_PORT,
      INSPECTIQ_MOCK: process.env.DROIDLENS_MOCK || process.env.INSPECTIQ_MOCK || 'false',
      INSPECTIQ_PORT: BACKEND_PORT,
    }

    backendProcess = spawn(
      python,
      ['-m', 'inspectiq.api.main'],
      {
        cwd: backendDir,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
      }
    )
    backendSpawnedByElectron = true

    backendProcess.stdout.on('data', (data) => {
      if (IS_DEV) console.log(`[backend] ${data.toString().trim()}`)
    })

    backendProcess.stderr.on('data', (data) => {
      if (IS_DEV) console.error(`[backend] ${data.toString().trim()}`)
    })

    backendProcess.on('error', (err) => {
      reject(new Error(`Failed to start Python backend: ${err.message}`))
    })

    backendProcess.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        console.error(`Backend exited with code ${code}`)
      }
      backendProcess = null
    })

    waitForBackend(30, 500).then(resolve).catch(reject)
  })
}

function getBackendDir() {
  if (IS_DEV) {
    return path.join(__dirname, '..', 'backend')
  }
  return path.join(process.resourcesPath, 'backend')
}

function getPythonCommand() {
  if (process.env.DROIDLENS_PYTHON || process.env.INSPECTIQ_PYTHON) {
    return process.env.DROIDLENS_PYTHON || process.env.INSPECTIQ_PYTHON
  }
  return process.platform === 'win32' ? 'python' : 'python3'
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
        reject(new Error('Backend failed to start within timeout'))
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
    const indexPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html')
    mainWindow.loadFile(indexPath)
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
      `${err.message}\n\nEnsure Python 3.10+ is installed and backend dependencies are available:\n  pip install -r backend/requirements.txt`
    )
    app.quit()
  }
}

app.setName(APP_NAME)
if (process.platform === 'win32') {
  app.setAppUserModelId('com.droidlens.desktop')
}

app.whenReady().then(bootstrap)

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
