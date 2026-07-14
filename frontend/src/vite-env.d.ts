/// <reference types="vite/client" />

declare const __DROIDLENS_VERSION__: string

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_WS_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

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
