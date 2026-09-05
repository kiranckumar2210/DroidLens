import { useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import { api } from '../api/client'
import { isXmlFile, stripExtension } from '../offline/xmlPackage'

export interface LocatorHealthIssue {
  severity: string
  code: string
  message: string
  element_path: string
  class_name: string
  resource_id?: string
  hint?: string
}

export interface LocatorHealthReport {
  screen_name: string
  node_count: number
  clickable_count: number
  score: number
  issue_count: number
  issues: LocatorHealthIssue[]
}

interface Props {
  open: boolean
  onClose: () => void
  initialXml?: string | null
  initialScreenName?: string
  onNotify?: (msg: string, kind?: 'success' | 'error' | 'warning') => void
}

export default function LocatorHealthDialog({
  open, onClose, initialXml, initialScreenName, onNotify,
}: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [reports, setReports] = useState<LocatorHealthReport[]>([])

  if (!open) return null

  const scanXml = async (xml: string, screenName: string) => api.locatorHealthScan(xml, screenName)

  const runScan = async () => {
    setLoading(true)
    setReports([])
    try {
      if (initialXml && !file) {
        const r = await scanXml(initialXml, initialScreenName || 'CurrentScreen')
        setReports([r])
        onNotify?.(`Health score: ${r.score}/100`, r.score >= 80 ? 'success' : 'warning')
        return
      }
      if (!file) {
        onNotify?.('Select an XML file or open a session first', 'warning')
        return
      }
      const xml = await file.text()
      const r = await scanXml(xml, stripExtension(file.name))
      setReports([r])
      onNotify?.(`Health score: ${r.score}/100`, r.score >= 80 ? 'success' : 'warning')
    } catch (e) {
      onNotify?.((e as Error).message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const scanFolder = async () => {
    const bridge = window.droidlens ?? window.inspectiq
    if (!bridge?.pickImportFolder || !bridge?.readFolderPairs) {
      onNotify?.('Folder scan requires the desktop app', 'warning')
      return
    }
    setLoading(true)
    setReports([])
    try {
      const folder = await bridge.pickImportFolder()
      if (!folder) return
      const pairs = await bridge.readFolderPairs(folder)
      const xmlPairs = pairs.filter((p) => p.xmlPath)
      if (!xmlPairs.length) {
        onNotify?.('No XML files in folder', 'warning')
        return
      }
      const next: LocatorHealthReport[] = []
      for (const pair of xmlPairs.slice(0, 20)) {
        const paths = await bridge.readPackagePaths!(pair.xmlPath!, pair.screenshotPath)
        if (paths?.xml) {
          next.push(await scanXml(paths.xml, pair.label))
        }
      }
      setReports(next)
      const avg = next.length ? Math.round(next.reduce((s, r) => s + r.score, 0) / next.length) : 0
      onNotify?.(`Scanned ${next.length} screens — avg score ${avg}/100`, 'success')
    } catch (e) {
      onNotify?.((e as Error).message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal locator-health-modal" onClick={(e) => e.stopPropagation()}>
        <h3><ShieldAlert size={18} /> Locator Health Scan</h3>
        <p className="field-hint">Find fragile locators, duplicate resource-ids, and missing accessibility labels.</p>

        {!initialXml && (
          <label className="field-label">
            XML file
            <input type="file" accept=".xml,.uix" onChange={(e) => {
              const f = e.target.files?.[0]
              if (f && isXmlFile(f.name)) setFile(f)
            }} />
            {file && <span className="file-picked">{file.name}</span>}
          </label>
        )}
        {initialXml && !file && (
          <p className="field-hint">Will scan the current inspector session XML.</p>
        )}

        <div className="modal-actions">
          <button type="button" onClick={onClose}>Close</button>
          <button type="button" className="btn-secondary" onClick={() => void scanFolder()} disabled={loading}>
            Scan Folder
          </button>
          <button type="button" className="primary" onClick={() => void runScan()} disabled={loading}>
            {loading ? 'Scanning…' : 'Scan'}
          </button>
        </div>

        {reports.length > 0 && (
          <div className="health-results">
            {reports.map((r) => (
              <section key={r.screen_name} className="health-report-card">
                <header>
                  <strong>{r.screen_name}</strong>
                  <span className={`health-score ${r.score >= 80 ? 'good' : r.score >= 50 ? 'warn' : 'bad'}`}>
                    {r.score}/100
                  </span>
                </header>
                <p className="field-hint">{r.node_count} nodes · {r.clickable_count} clickable · {r.issue_count} issues</p>
                <ul className="health-issue-list">
                  {r.issues.slice(0, 15).map((issue, i) => (
                    <li key={`${issue.code}-${i}`} className={`severity-${issue.severity}`}>
                      <span className="issue-code">{issue.code}</span>
                      {issue.message}
                      {issue.hint && <em>{issue.hint}</em>}
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
