const { contextBridge, ipcRenderer } = require('electron')
const pkg = require('../package.json')

const APP_VERSION = pkg.version || '2.0.0'
const BACKEND_PORT = process.env.DROIDLENS_PORT || process.env.INSPECTIQ_PORT || '8765'

function readCloudApiUrl() {
  const arg = process.argv.find((entry) => entry.startsWith('--cloud-api-url='))
  if (arg) {
    const value = arg.slice('--cloud-api-url='.length).trim()
    return value || undefined
  }
  const fromEnv = process.env.DROIDLENS_CLOUD_API_URL || process.env.DROIDLENS_AUTH_API_URL
  return fromEnv ? fromEnv.replace(/\/$/, '') : undefined
}

const localApiBase = `http://127.0.0.1:${BACKEND_PORT}`
const cloudApiUrl = readCloudApiUrl()

const bridge = {
  isElectron: true,
  apiBase: localApiBase,
  wsBase: `ws://127.0.0.1:${BACKEND_PORT}`,
  authApiBase: cloudApiUrl || localApiBase,
  version: APP_VERSION,
  productName: 'DroidLens',
  tagline: 'See. Inspect. Automate.',
  pickExportFolder: () => ipcRenderer.invoke('pick-export-folder'),
  pickImportFolder: () => ipcRenderer.invoke('pick-import-folder'),
  exportXmlPackage: (payload) => ipcRenderer.invoke('export-xml-package', payload),
  readFolderPairs: (folderPath) => ipcRenderer.invoke('read-folder-pairs', folderPath),
  readPackagePaths: (xmlPath, screenshotPath) =>
    ipcRenderer.invoke('read-package-paths', { xmlPath, screenshotPath }),
}

contextBridge.exposeInMainWorld('droidlens', bridge)
contextBridge.exposeInMainWorld('inspectiq', bridge)
