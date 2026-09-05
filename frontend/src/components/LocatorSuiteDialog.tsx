import { useState } from 'react'
import { CheckCircle, Download } from 'lucide-react'
import { api } from '../api/client'
import { downloadSuite, parseLocatorSuite, type LocatorSuite } from '../locators/suite'
import { isXmlFile, stripExtension } from '../offline/xmlPackage'

interface ValidationResult {
  passed: number
  failed: number
  total: number
  ok: boolean
  results: Array<{
    screen: string
    element_name: string
    locator_type: string
    value: string
    valid: boolean
    match_count: number
    error?: string
    warning?: string
  }>
}

interface Props {
  open: boolean
  onClose: () => void
  initialXml?: string | null
  initialScreenName?: string
  onNotify?: (msg: string, kind?: 'success' | 'error' | 'warning') => void
}

export default function LocatorSuiteDialog({
  open, onClose, initialXml, initialScreenName, onNotify,
}: Props) {
  const [xmlFile, setXmlFile] = useState<File | null>(null)
  const [suiteFile, setSuiteFile] = useState<File | null>(null)
  const [suite, setSuite] = useState<LocatorSuite | null>(null)
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<ValidationResult | null>(null)

  if (!open) return null

  const loadSuiteFile = async (file: File) => {
    setSuiteFile(file)
    try {
      const parsed = parseLocatorSuite(JSON.parse(await file.text()))
      setSuite(parsed)
    } catch {
      setSuite(null)
      onNotify?.('Invalid locator suite JSON', 'error')
    }
  }

  const runValidate = async () => {
    setLoading(true)
    setReport(null)
    try {
      let xml = initialXml ?? ''
      let screenName = initialScreenName ?? 'Screen'
      if (xmlFile) {
        xml = await xmlFile.text()
        screenName = stripExtension(xmlFile.name)
      }
      if (!xml) {
        onNotify?.('Select an XML file or open a session', 'warning')
        return
      }
      let locators: LocatorSuite | null = suite
      if (!locators && suiteFile) {
        locators = parseLocatorSuite(JSON.parse(await suiteFile.text()))
      }
      if (!locators) {
        onNotify?.('Select a locator suite JSON file', 'warning')
        return
      }
      const result = await api.validateLocatorsOffline(xml, locators, screenName)
      setReport(result)
      onNotify?.(
        result.ok ? `All ${result.total} locators passed` : `${result.failed} of ${result.total} failed`,
        result.ok ? 'success' : 'warning',
      )
    } catch (e) {
      onNotify?.((e as Error).message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const exportTemplate = () => {
    const template = {
      format: 'droidlens-locator-suite',
      formatVersion: 1,
      project: 'MyApp',
      screens: [{
        name: initialScreenName ?? 'LoginScreen',
        xml_file: `${initialScreenName ?? 'LoginScreen'}.xml`,
        elements: [
          { name: 'login_button', locator_type: 'resource_id', value: 'com.example:id/login' },
        ],
      }],
    } as LocatorSuite
    downloadSuite(template, 'locators.template.json')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal locator-suite-modal" onClick={(e) => e.stopPropagation()}>
        <h3><CheckCircle size={18} /> Validate Locator Suite</h3>
        <p className="field-hint">
          Validate a <code>locators.json</code> suite against UIAutomator XML — same checks as the CI CLI.
        </p>

        {!initialXml && (
          <label className="field-label">
            XML dump
            <input type="file" accept=".xml,.uix" onChange={(e) => {
              const f = e.target.files?.[0]
              if (f && isXmlFile(f.name)) setXmlFile(f)
            }} />
          </label>
        )}
        {initialXml && <p className="field-hint">Using current inspector session XML.</p>}

        <label className="field-label">
          Locator suite JSON
          <input type="file" accept=".json" onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) void loadSuiteFile(f)
          }} />
        </label>

        <div className="suite-actions-row">
          <button type="button" className="btn-secondary btn-sm" onClick={exportTemplate}>
            <Download size={14} /> Template
          </button>
        </div>

        <div className="modal-actions">
          <button type="button" onClick={onClose}>Close</button>
          <button type="button" className="primary" onClick={() => void runValidate()} disabled={loading}>
            {loading ? 'Validating…' : 'Validate'}
          </button>
        </div>

        {report && (
          <div className="suite-report">
            <p><strong>{report.passed}/{report.total}</strong> passed</p>
            <ul>
              {report.results.map((r, i) => (
                <li key={i} className={r.valid ? 'ok' : 'fail'}>
                  {r.valid ? '✓' : '✗'} {r.element_name}: {r.match_count} match(es)
                  {r.error && ` — ${r.error}`}
                  {!r.error && r.warning && ` — ${r.warning}`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
