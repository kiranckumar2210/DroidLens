import { useState } from 'react'
import { Wrench } from 'lucide-react'
import { api } from '../api/client'
import { isXmlFile } from '../offline/xmlPackage'
import type { LocatorCandidate } from '../types'

interface MigrationResult {
  status: string
  message: string
  old_match_count: number
  new_match_count: number
  suggestions: Array<{
    reason: string
    element_id: string
    resource_id?: string
    class_name: string
    locators: Array<{
      locator_type: string
      value: string
      display_name: string
      recommended: boolean
      overall_score: number
    }>
  }>
}

interface Props {
  open: boolean
  onClose: () => void
  onNotify?: (msg: string, kind?: 'success' | 'error' | 'warning') => void
  onApplyLocator?: (loc: LocatorCandidate) => void
}

export default function LocatorMigrateDialog({ open, onClose, onNotify, onApplyLocator }: Props) {
  const [oldFile, setOldFile] = useState<File | null>(null)
  const [newFile, setNewFile] = useState<File | null>(null)
  const [locatorType, setLocatorType] = useState('xpath')
  const [locatorValue, setLocatorValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MigrationResult | null>(null)

  if (!open) return null

  const runMigrate = async () => {
    if (!oldFile || !newFile || !locatorValue.trim()) {
      onNotify?.('Provide old XML, new XML, and the broken locator', 'warning')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const [oldXml, newXml] = await Promise.all([oldFile.text(), newFile.text()])
      const r = await api.locatorMigrate(oldXml, newXml, locatorType, locatorValue.trim())
      setResult(r)
      onNotify?.(r.message, r.status === 'ok' ? 'success' : 'warning')
    } catch (e) {
      onNotify?.((e as Error).message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal locator-migrate-modal" onClick={(e) => e.stopPropagation()}>
        <h3><Wrench size={18} /> Locator Migration Assistant</h3>
        <p className="field-hint">
          Compare old vs new XML dumps and get ranked replacement locators when a selector breaks.
        </p>

        <div className="xml-diff-pickers">
          <label className="field-label">
            Baseline XML (old build)
            <input type="file" accept=".xml,.uix" onChange={(e) => {
              const f = e.target.files?.[0]
              if (f && isXmlFile(f.name)) setOldFile(f)
            }} />
            {oldFile && <span className="file-picked">{oldFile.name}</span>}
          </label>
          <label className="field-label">
            New XML (current build)
            <input type="file" accept=".xml,.uix" onChange={(e) => {
              const f = e.target.files?.[0]
              if (f && isXmlFile(f.name)) setNewFile(f)
            }} />
            {newFile && <span className="file-picked">{newFile.name}</span>}
          </label>
        </div>

        <label className="field-label">Broken locator</label>
        <div className="migrate-locator-row">
          <select value={locatorType} onChange={(e) => setLocatorType(e.target.value)}>
            <option value="xpath">XPath</option>
            <option value="uiautomator2">UiSelector</option>
            <option value="resource_id">Resource ID</option>
            <option value="text">Text</option>
          </select>
          <input
            className="full-width"
            placeholder="Locator expression…"
            value={locatorValue}
            onChange={(e) => setLocatorValue(e.target.value)}
          />
        </div>

        <div className="modal-actions">
          <button type="button" onClick={onClose}>Close</button>
          <button type="button" className="primary" onClick={() => void runMigrate()} disabled={loading}>
            {loading ? 'Analyzing…' : 'Find Replacements'}
          </button>
        </div>

        {result && (
          <div className="migrate-results">
            <p className={`migrate-status status-${result.status}`}>{result.message}</p>
            {result.suggestions.map((s, i) => (
              <section key={i} className="migrate-suggestion">
                <h4>{s.resource_id || s.class_name}</h4>
                <p className="field-hint">{s.reason}</p>
                <ul>
                  {s.locators.map((loc, j) => (
                    <li key={j}>
                      <button
                        type="button"
                        className="migrate-loc-btn"
                        onClick={() => {
                          onApplyLocator?.({
                            locator_type: loc.locator_type,
                            value: loc.value,
                            display_name: loc.display_name,
                            scores: { stability: loc.overall_score, uniqueness: loc.overall_score, maintainability: loc.overall_score, overall: loc.overall_score },
                            recommended: loc.recommended,
                            reason: '',
                          })
                          onNotify?.('Locator applied to inspector', 'success')
                        }}
                      >
                        {loc.recommended && '★ '}{loc.display_name} ({Math.round(loc.overall_score * 100)}%)
                      </button>
                      <code className="mono">{loc.value}</code>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
