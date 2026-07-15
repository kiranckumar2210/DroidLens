/// <reference types="vite/client" />

declare const __DROIDLENS_VERSION__: string

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_AUTH_API_BASE?: string
  readonly VITE_WS_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface FolderXmlPair {
  label: string
  xmlPath: string
  screenshotPath: string | null
}

interface ExportXmlPackagePayload {
  parentDir: string
  folderName: string
  baseName: string
  xml: string
  screenshotBase64: string
  metadata?: Record<string, unknown>
}

interface DroidLensBridge {
  isElectron: boolean
  apiBase: string
  wsBase: string
  authApiBase?: string
  version: string
  productName?: string
  tagline?: string
  pickExportFolder?: () => Promise<string | null>
  pickImportFolder?: () => Promise<string | null>
  exportXmlPackage?: (payload: ExportXmlPackagePayload) => Promise<string>
  readFolderPairs?: (folderPath: string) => Promise<FolderXmlPair[]>
  readPackagePaths?: (xmlPath: string, screenshotPath?: string | null) => Promise<{
    xml: string
    screenshotBase64: string | null
    xmlPath: string
    screenshotPath: string | null
  }>
}

interface Window {
  droidlens?: DroidLensBridge
  inspectiq?: DroidLensBridge
}
