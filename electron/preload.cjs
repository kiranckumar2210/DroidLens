const { contextBridge } = require('electron')
const pkg = require('../package.json')

const APP_VERSION = pkg.version || '1.0.0'

contextBridge.exposeInMainWorld('droidlens', {
  isElectron: true,
  apiBase: `http://127.0.0.1:${process.env.DROIDLENS_PORT || process.env.INSPECTIQ_PORT || '8765'}`,
  wsBase: `ws://127.0.0.1:${process.env.DROIDLENS_PORT || process.env.INSPECTIQ_PORT || '8765'}`,
  version: APP_VERSION,
  productName: 'DroidLens',
  tagline: 'See. Inspect. Automate.',
})

// Backward compatibility (legacy InspectIQ preload API)
contextBridge.exposeInMainWorld('inspectiq', {
  isElectron: true,
  apiBase: `http://127.0.0.1:${process.env.DROIDLENS_PORT || process.env.INSPECTIQ_PORT || '8765'}`,
  wsBase: `ws://127.0.0.1:${process.env.DROIDLENS_PORT || process.env.INSPECTIQ_PORT || '8765'}`,
  version: APP_VERSION,
  productName: 'DroidLens',
})
