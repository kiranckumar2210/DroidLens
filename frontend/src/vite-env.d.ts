/// <reference types="vite/client" />

declare const __DROIDLENS_VERSION__: string

interface DroidLensBridge {
  isElectron: boolean
  apiBase: string
  wsBase: string
  version: string
  productName?: string
  tagline?: string
}

interface Window {
  droidlens?: DroidLensBridge
  inspectiq?: DroidLensBridge
}
