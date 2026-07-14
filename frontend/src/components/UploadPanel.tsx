import { Upload } from 'lucide-react'

interface Props {
  onUpload: (xml?: File, screenshot?: File) => Promise<void>
  loading: boolean
}

export default function UploadPanel({ onUpload, loading }: Props) {
  const handleFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    let xml: File | undefined
    let screenshot: File | undefined
    for (const f of Array.from(files)) {
      if (f.name.endsWith('.xml') || f.type.includes('xml')) xml = f
      else if (f.type.startsWith('image/')) screenshot = f
    }
    await onUpload(xml, screenshot)
    e.target.value = ''
  }

  return (
    <div className="panel upload-panel">
      <div className="panel-header">Open XML Dump</div>
      <div className="upload-body">
        <p className="upload-hint">
          Load a UI hierarchy XML dump with optional screenshot for offline inspection.
        </p>
        <label className="upload-btn">
          <Upload size={16} />
          {loading ? 'Loading...' : 'Choose XML / Screenshot'}
          <input type="file" accept=".xml,.uix,image/*" multiple hidden onChange={handleFiles} disabled={loading} />
        </label>
        <ul className="upload-list">
          <li>XML only — tree inspection</li>
          <li>Screenshot only — visual reference</li>
          <li>Both — aligned highlight on screenshot</li>
        </ul>
      </div>
    </div>
  )
}
