import { useState } from 'react'
import { GitCompare } from 'lucide-react'
import { api } from '../api/client'
import { isXmlFile } from '../offline/xmlPackage'

export interface XmlDiffResult {
  baseline_node_count: number
  compare_node_count: number
  added_count: number
  removed_count: number
  changed_count: number
  unchanged_count: number
  added: Array<{ path: string; class_name: string; resource_id?: string; text?: string }>
  removed: Array<{ path: string; class_name: string; resource_id?: string; text?: string }>
  changed: Array<{ key: string; fields: string[]; baseline: Record<string, unknown>; compare: Record<string, unknown> }>
}

interface Props {
  open: boolean
  onClose: () => void
  onNotify?: (msg: string, kind?: 'success' | 'error' | 'warning') => void
}

async function readXmlFile(file: File): Promise<string> {
  return file.text()
}

export default function XmlDiffDialog({ open, onClose, onNotify }: Props) {
  const [baseline, setBaseline] = useState<File | null>(null)
  const [compare, setCompare] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<XmlDiffResult | null>(null)

  if (!open) return null

  const runDiff = async () => {
    if (!baseline || !compare) {
      onNotify?.('Select baseline and compare XML files', 'warning')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const [baseXml, compareXml] = await Promise.all([readXmlFile(baseline), readXmlFile(compare)])
      const diff = await api.xmlDiff(baseXml, compareXml)
      setResult(diff)
      onNotify?.('XML diff complete', 'success')
    } catch (e) {
      onNotify?.((e as Error).message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const pick = (kind: 'baseline' | 'compare', file: File | undefined) => {
    if (!file || !isXmlFile(file.name)) return
    if (kind === 'baseline') setBaseline(file)
    else setCompare(file)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal xml-diff-modal" onClick={(e) => e.stopPropagation()}>
        <h3><GitCompare size={18} /> Compare XML Dumps</h3>
        <p className="field-hint">Compare two UIAutomator XML files to find added, removed, and changed elements.</p>

        <div className="xml-diff-pickers">
          <label className="field-label">
            Baseline (older)
            <input type="file" accept=".xml,.uix" onChange={(e) => pick('baseline', e.target.files?.[0])} />
            {baseline && <span className="file-picked">{baseline.name}</span>}
          </label>
          <label className="field-label">
            Compare (newer)
            <input type="file" accept=".xml,.uix" onChange={(e) => pick('compare', e.target.files?.[0])} />
            {compare && <span className="file-picked">{compare.name}</span>}
          </label>
        </div>

        <div className="modal-actions">
          <button type="button" onClick={onClose}>Close</button>
          <button type="button" className="primary" onClick={() => void runDiff()} disabled={loading}>
            {loading ? 'Comparing…' : 'Compare'}
          </button>
        </div>

        {result && (
          <div className="xml-diff-results">
            <div className="xml-diff-stats">
              <span>Baseline: {result.baseline_node_count} nodes</span>
              <span>Compare: {result.compare_node_count} nodes</span>
              <span className="added">+{result.added_count} added</span>
              <span className="removed">−{result.removed_count} removed</span>
              <span className="changed">~{result.changed_count} changed</span>
              <span>{result.unchanged_count} unchanged</span>
            </div>
            {result.removed.length > 0 && (
              <section>
                <h4>Removed</h4>
                <ul>{result.removed.slice(0, 20).map((n, i) => (
                  <li key={`r-${i}`}><code>{n.resource_id || n.class_name}</code> {n.text && `— ${n.text.slice(0, 40)}`}</li>
                ))}</ul>
              </section>
            )}
            {result.added.length > 0 && (
              <section>
                <h4>Added</h4>
                <ul>{result.added.slice(0, 20).map((n, i) => (
                  <li key={`a-${i}`}><code>{n.resource_id || n.class_name}</code> {n.text && `— ${n.text.slice(0, 40)}`}</li>
                ))}</ul>
              </section>
            )}
            {result.changed.length > 0 && (
              <section>
                <h4>Changed</h4>
                <ul>{result.changed.slice(0, 20).map((c, i) => (
                  <li key={`c-${i}`}><code>{c.key}</code> — {c.fields.join(', ')}</li>
                ))}</ul>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
