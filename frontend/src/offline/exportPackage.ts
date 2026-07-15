import { isElectron } from '../api/baseUrl'
import { buildExportMetadata, formatExportFolderName, stripExtension } from './xmlPackage'

export interface ExportPackageInput {
  xml: string
  screenshotBase64: string
  baseName?: string
  screenWidth?: number
  screenHeight?: number
  screenshotWidth?: number
  screenshotHeight?: number
  packageName?: string
  deviceId?: string
  mode?: string
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** Browser fallback — downloads XML, PNG, and optional metadata.json separately. */
function exportViaBrowser(input: ExportPackageInput, baseName: string): void {
  const metadata = buildExportMetadata({
    baseName,
    screenWidth: input.screenWidth,
    screenHeight: input.screenHeight,
    screenshotWidth: input.screenshotWidth,
    screenshotHeight: input.screenshotHeight,
    packageName: input.packageName,
    deviceId: input.deviceId,
    mode: input.mode,
  })

  downloadBlob(new Blob([input.xml], { type: 'application/xml' }), `${baseName}.xml`)
  const pngBytes = Uint8Array.from(atob(input.screenshotBase64), (c) => c.charCodeAt(0))
  downloadBlob(new Blob([pngBytes], { type: 'image/png' }), `${baseName}.png`)
  downloadBlob(
    new Blob([JSON.stringify(metadata, null, 2)], { type: 'application/json' }),
    `${baseName}-metadata.json`,
  )
}

/** Export XML package to user-selected folder (Electron) or browser downloads. */
export async function exportXmlPackage(input: ExportPackageInput): Promise<string> {
  const baseName = stripExtension(input.baseName || 'CurrentScreen')
  const metadata = buildExportMetadata({
    baseName,
    screenWidth: input.screenWidth,
    screenHeight: input.screenHeight,
    screenshotWidth: input.screenshotWidth,
    screenshotHeight: input.screenshotHeight,
    packageName: input.packageName,
    deviceId: input.deviceId,
    mode: input.mode,
  })

  const bridge = window.droidlens ?? window.inspectiq
  if (isElectron() && bridge?.pickExportFolder && bridge?.exportXmlPackage) {
    const parentDir = await bridge.pickExportFolder()
    if (!parentDir) throw new Error('Export cancelled')
    const folderName = formatExportFolderName(baseName)
    const outPath = await bridge.exportXmlPackage({
      parentDir,
      folderName,
      baseName,
      xml: input.xml,
      screenshotBase64: input.screenshotBase64,
      metadata,
    })
    return outPath
  }

  exportViaBrowser(input, baseName)
  return `${baseName}.xml + ${baseName}.png (downloads)`
}
