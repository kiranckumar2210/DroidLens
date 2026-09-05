import { useState } from 'react'
import { Download } from 'lucide-react'
import { api } from '../api/client'
import {
  downloadText,
  formatForExport,
  type ExportFormat,
  type RepositoryElement,
} from '../locators/exportFormats'
import type { ElementInspectionResult } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  inspection: ElementInspectionResult | null
  screenName?: string
  packageName?: string
  elementName?: string
  onNotify?: (msg: string, kind?: 'success' | 'error' | 'warning') => void
}

const FORMATS: { id: ExportFormat; label: string }[] = [
  { id: 'json', label: 'JSON' },
  { id: 'csv', label: 'CSV' },
  { id: 'markdown', label: 'Markdown' },
]

export default function LocatorExportModal({
  open,
  onClose,
  inspection,
  screenName,
  packageName,
  elementName,
  onNotify,
}: Props) {
  const [format, setFormat] = useState<ExportFormat>('json')
  const [scope, setScope] = useState<'element' | 'repository'>('element')
  const [loading, setLoading] = useState(false)

  if (!open) return null

  const handleExport = async () => {
    setLoading(true)
    try {
      let repository: RepositoryElement[] | null = null
      if (scope === 'repository') {
        const res = await api.getLocatorRepository()
        repository = res.elements as unknown as RepositoryElement[]
        if (!repository.length) {
          onNotify?.('Repository is empty — save elements first', 'warning')
          return
        }
      } else if (!inspection) {
        onNotify?.('Select an element to export locators', 'warning')
        return
      }

      const result = formatForExport(format, scope === 'element' ? inspection : null, repository, {
        screenName,
        packageName,
        elementName,
      })
      if (!result) {
        onNotify?.('Nothing to export', 'warning')
        return
      }
      downloadText(result.content, result.filename, result.mime)
      onNotify?.(`Exported ${result.filename}`, 'success')
      onClose()
    } catch (e) {
      onNotify?.((e as Error).message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal locator-export-modal" onClick={(e) => e.stopPropagation()}>
        <h3><Download size={18} /> Export Locators</h3>
        <p className="field-hint">Export current element locators or your full saved repository.</p>

        <label className="field-label">Scope</label>
        <div className="export-scope-tabs">
          <button
            type="button"
            className={scope === 'element' ? 'active' : ''}
            onClick={() => setScope('element')}
            disabled={!inspection}
          >
            Current Element
          </button>
          <button
            type="button"
            className={scope === 'repository' ? 'active' : ''}
            onClick={() => setScope('repository')}
          >
            Full Repository
          </button>
        </div>

        <label className="field-label">Format</label>
        <div className="export-format-tabs">
          {FORMATS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={format === f.id ? 'active' : ''}
              onClick={() => setFormat(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="modal-actions">
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="button" className="primary" onClick={() => void handleExport()} disabled={loading}>
            {loading ? 'Exporting…' : 'Download'}
          </button>
        </div>
      </div>
    </div>
  )
}
