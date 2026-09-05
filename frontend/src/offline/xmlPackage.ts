/** UIAutomatorViewer-style XML + screenshot pairing utilities. */

export interface XmlPackagePair {
  id: string
  label: string
  xml?: File
  screenshot?: File
  xmlPath?: string
  screenshotPath?: string
}

export function isXmlFile(name: string): boolean {
  const lower = name.toLowerCase()
  return lower.endsWith('.xml') || lower.endsWith('.uix')
}

export function isImageFile(name: string, mime = ''): boolean {
  const lower = name.toLowerCase()
  return mime.startsWith('image/') || lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')
}

export function stripExtension(filename: string): string {
  const i = filename.lastIndexOf('.')
  return i > 0 ? filename.slice(0, i) : filename
}

export function findMatchingScreenshot(xmlFile: File, candidates: File[]): File | undefined {
  const base = stripExtension(xmlFile.name).toLowerCase()
  return candidates.find((f) => {
    if (!isImageFile(f.name, f.type)) return false
    return stripExtension(f.name).toLowerCase() === base
  })
}

export function pairFilesFromList(files: File[]): XmlPackagePair[] {
  const xmlFiles = files.filter((f) => isXmlFile(f.name))
  const images = files.filter((f) => isImageFile(f.name, f.type))
  return xmlFiles.map((xml, idx) => {
    const shot = findMatchingScreenshot(xml, images)
    const label = stripExtension(xml.name)
    return {
      id: `${label}-${idx}`,
      label,
      xml,
      screenshot: shot,
    }
  })
}

export function formatExportFolderName(baseName: string): string {
  const safe = baseName.replace(/[^\w\-]+/g, '_').replace(/^_|_$/g, '') || 'Screen'
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  return `${safe}_${stamp}`
}

export function buildExportMetadata(opts: {
  baseName: string
  screenWidth?: number
  screenHeight?: number
  screenshotWidth?: number
  screenshotHeight?: number
  packageName?: string
  deviceId?: string
  mode?: string
  notes?: string
}) {
  return {
    format: 'droidlens-xml-package',
    formatVersion: 1,
    screenName: opts.baseName,
    captureTimestamp: new Date().toISOString(),
    xmlFile: `${opts.baseName}.xml`,
    screenshotFile: `${opts.baseName}.png`,
    notes: opts.notes?.trim() || null,
    screenWidth: opts.screenWidth ?? 0,
    screenHeight: opts.screenHeight ?? 0,
    screenshotWidth: opts.screenshotWidth ?? 0,
    screenshotHeight: opts.screenshotHeight ?? 0,
    packageName: opts.packageName ?? null,
    sourceDeviceId: opts.deviceId ?? null,
    sourceMode: opts.mode ?? null,
    tool: 'DroidLens',
  }
}

export async function fileToBase64(file: File): Promise<string> {
  const buf = await file.arrayBuffer()
  const bytes = new Uint8Array(buf)
  let binary = ''
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]!)
  return btoa(binary)
}

export function base64ToFile(b64: string, filename: string, mime = 'image/png'): File {
  const binary = atob(b64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
  return new File([bytes], filename, { type: mime })
}

export function xmlStringToFile(content: string, filename: string): File {
  return new File([content], filename, { type: 'application/xml' })
}
