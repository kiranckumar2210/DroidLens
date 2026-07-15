import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FolderOpen, Image, Upload } from 'lucide-react'
import { isElectron } from '../api/baseUrl'
import {
  findMatchingScreenshot,
  isImageFile,
  isXmlFile,
  pairFilesFromList,
  stripExtension,
  type XmlPackagePair,
} from '../offline/xmlPackage'

interface Props {
  open: boolean
  onClose: () => void
  onOpen: (pairs: XmlPackagePair[], startIndex?: number) => Promise<void>
}

export default function ImportXmlPackageDialog({ open, onClose, onOpen }: Props) {
  const [xmlFile, setXmlFile] = useState<File | null>(null)
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null)
  const [poolFiles, setPoolFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const xmlInputRef = useRef<HTMLInputElement>(null)
  const shotInputRef = useRef<HTMLInputElement>(null)

  const previewUrl = useMemo(() => {
    if (!screenshotFile) return null
    return URL.createObjectURL(screenshotFile)
  }, [screenshotFile])

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  const reset = useCallback(() => {
    setXmlFile(null)
    setScreenshotFile(null)
    setPoolFiles([])
    setError(null)
  }, [])

  useEffect(() => {
    if (!open) reset()
  }, [open, reset])

  const applyXml = (file: File, pool: File[]) => {
    setXmlFile(file)
    const match = findMatchingScreenshot(file, pool.length ? pool : [file])
    if (match) setScreenshotFile(match)
  }

  const handleXmlPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    applyXml(file, poolFiles)
    e.target.value = ''
  }

  const handleShotPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) setScreenshotFile(file)
    e.target.value = ''
  }

  const handleFolderPick = async () => {
    const bridge = window.droidlens ?? window.inspectiq
    if (!isElectron() || !bridge?.pickImportFolder || !bridge?.readFolderPairs) return
    setError(null)
    const folder = await bridge.pickImportFolder()
    if (!folder) return
    const pairs = await bridge.readFolderPairs(folder)
    if (!pairs.length) {
      setError('No XML files found in that folder')
      return
    }
    const mapped: XmlPackagePair[] = pairs.map((p, idx) => ({
      id: `${p.label}-${idx}`,
      label: p.label,
      xmlPath: p.xmlPath,
      screenshotPath: p.screenshotPath ?? undefined,
    }))
    setLoading(true)
    try {
      await onOpen(mapped, 0)
      onClose()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    if (!files.length) return
    setPoolFiles(files)
    const xml = files.find((f) => isXmlFile(f.name))
    if (xml) applyXml(xml, files)
    else {
      const img = files.find((f) => isImageFile(f.name, f.type))
      if (img) setScreenshotFile(img)
    }
  }

  const handleOpen = async () => {
    if (!xmlFile) {
      setError('Select an XML hierarchy file')
      return
    }
    if (!screenshotFile) {
      const proceed = window.confirm('Screenshot not found.\n\nContinue with XML only?')
      if (!proceed) return
    }
    setLoading(true)
    setError(null)
    try {
      const pair: XmlPackagePair = {
        id: stripExtension(xmlFile.name),
        label: stripExtension(xmlFile.name),
        xml: xmlFile,
        screenshot: screenshotFile ?? undefined,
      }
      await onOpen([pair], 0)
      onClose()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const handleMultiFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (!files.length) return
    setPoolFiles(files)
    const pairs = pairFilesFromList(files)
    if (pairs.length > 1) {
      setLoading(true)
      void onOpen(pairs, 0).then(onClose).catch((err) => {
        setError((err as Error).message)
      }).finally(() => {
        setLoading(false)
        e.target.value = ''
      })
      return
    }
    const xml = files.find((f) => isXmlFile(f.name))
    if (xml) applyXml(xml, files)
    e.target.value = ''
  }

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal import-xml-modal"
        onClick={(e) => e.stopPropagation()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <h3>Open XML Package</h3>
        <p className="modal-subtitle">
          Import a UIAutomator-style XML dump with matching PNG screenshot. Drop files here or browse.
        </p>

        <div className="import-drop-zone">
          <Upload size={28} aria-hidden />
          <p>Drag &amp; drop <strong>.xml</strong> + <strong>.png</strong> (matching names auto-pair)</p>
          <input
            type="file"
            multiple
            accept=".xml,.uix,image/*"
            hidden
            id="import-multi-input"
            onChange={handleMultiFileInput}
          />
          <label htmlFor="import-multi-input" className="btn-secondary btn-sm">Browse files…</label>
        </div>

        <div className="form-grid import-file-row">
          <label>
            XML hierarchy
            <div className="import-browse-row">
              <input ref={xmlInputRef} type="file" accept=".xml,.uix" hidden onChange={handleXmlPick} />
              <button type="button" className="btn-secondary btn-sm" onClick={() => xmlInputRef.current?.click()}>
                Browse XML
              </button>
              <span className="import-file-name">{xmlFile?.name || 'None selected'}</span>
            </div>
          </label>
          <label>
            Screenshot
            <div className="import-browse-row">
              <input ref={shotInputRef} type="file" accept="image/*" hidden onChange={handleShotPick} />
              <button type="button" className="btn-secondary btn-sm" onClick={() => shotInputRef.current?.click()}>
                <Image size={14} /> Browse PNG
              </button>
              <span className="import-file-name">{screenshotFile?.name || 'Auto-detect or none'}</span>
            </div>
          </label>
        </div>

        {previewUrl && (
          <div className="import-preview">
            <img src={previewUrl} alt="Screenshot preview" />
          </div>
        )}

        {!screenshotFile && xmlFile && (
          <p className="import-hint">No matching screenshot — you can continue with XML only.</p>
        )}

        {error && <div className="dashboard-error" role="alert">{error}</div>}

        <div className="modal-actions">
          {isElectron() && (
            <button type="button" className="btn-secondary" onClick={() => void handleFolderPick()} disabled={loading}>
              <FolderOpen size={14} /> Open Folder…
            </button>
          )}
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" className="primary" onClick={() => void handleOpen()} disabled={loading || !xmlFile}>
            {loading ? 'Opening…' : 'Open Inspector'}
          </button>
        </div>
      </div>
    </div>
  )
}
