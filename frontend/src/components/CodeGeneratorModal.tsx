import { useMemo, useState } from 'react'
import { Copy, Download, Search, X } from 'lucide-react'

const FRAMEWORKS = [
  { id: 'python_uiautomator2', label: 'Python — UIAutomator2', group: 'Python' },
  { id: 'python_appium', label: 'Python — Appium', group: 'Python' },
  { id: 'java_uiautomator', label: 'Java — UIAutomator', group: 'Java' },
  { id: 'java_appium', label: 'Java — Appium', group: 'Java' },
  { id: 'javascript_wdio', label: 'JavaScript — WebdriverIO', group: 'JavaScript' },
  { id: 'javascript_appium', label: 'JavaScript — Appium', group: 'JavaScript' },
  { id: 'adb_shell', label: 'ADB Shell', group: 'Shell' },
]

const ACTIONS = [
  'click', 'long_click', 'double_click', 'set_text', 'clear_text',
  'wait_for_element', 'exists', 'assert_exists',
  'scroll', 'swipe', 'drag', 'screenshot',
  'press_back', 'press_home', 'open_notification',
  'launch_app', 'close_app',
  'get_text', 'get_attribute', 'is_displayed', 'is_enabled', 'is_selected',
]

interface Props {
  open: boolean
  onClose: () => void
  code: string
  pageObject: string
  languageProfile: string
  action: string
  onLanguageChange: (profile: string) => void
  onActionChange: (action: string) => void
  elementName?: string
}

export default function CodeGeneratorModal({
  open, onClose, code, pageObject, languageProfile, action,
  onLanguageChange, onActionChange, elementName,
}: Props) {
  const [search, setSearch] = useState('')
  const [showPom, setShowPom] = useState(false)

  const fullCode = showPom && pageObject ? `${code}\n\n# --- Page Object ---\n${pageObject}` : code

  const lines = useMemo(() => {
    const src = fullCode || ''
    if (!search.trim()) return src.split('\n')
    const q = search.toLowerCase()
    return src.split('\n').map((line, i) => ({ n: i + 1, line, hit: line.toLowerCase().includes(q) }))
  }, [fullCode, search])

  if (!open) return null

  const copy = () => navigator.clipboard.writeText(fullCode)
  const ext = languageProfile.startsWith('java') ? 'java'
    : languageProfile.startsWith('javascript') ? 'js'
    : languageProfile === 'adb_shell' ? 'sh'
    : 'py'
  const save = () => {
    const blob = new Blob([fullCode], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${elementName || 'automation'}_${action}.${ext}`
    a.click()
  }

  const groups = [...new Set(FRAMEWORKS.map((f) => f.group))]

  return (
    <div className="modal-overlay code-modal-overlay" onClick={onClose}>
      <div className="modal code-modal" onClick={(e) => e.stopPropagation()}>
        <div className="code-modal-header">
          <h3>Code Generator</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="code-modal-toolbar">
          <select value={languageProfile} onChange={(e) => onLanguageChange(e.target.value)} aria-label="Framework">
            {groups.map((g) => (
              <optgroup key={g} label={g}>
                {FRAMEWORKS.filter((f) => f.group === g).map((f) => (
                  <option key={f.id} value={f.id}>{f.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
          <select value={action} onChange={(e) => onActionChange(e.target.value)} aria-label="Action">
            {ACTIONS.map((a) => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
          </select>
          <label className="pom-toggle">
            <input type="checkbox" checked={showPom} onChange={(e) => setShowPom(e.target.checked)} />
            Page Object
          </label>
          <div className="code-search">
            <Search size={14} />
            <input placeholder="Search code..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <button onClick={copy}><Copy size={14} /> Copy</button>
          <button onClick={save}><Download size={14} /> Save</button>
        </div>

        <div className="code-viewer">
          <pre className="code-block-with-lines mono">
            {Array.isArray(lines) && typeof lines[0] === 'object'
              ? (lines as { n: number; line: string; hit: boolean }[]).map((l) => (
                  <div key={l.n} className={`code-line ${l.hit ? 'highlight-line' : ''}`}>
                    <span className="line-num">{l.n}</span>
                    <span>{l.line}</span>
                  </div>
                ))
              : (lines as string[]).map((line, i) => (
                  <div key={i} className="code-line">
                    <span className="line-num">{i + 1}</span>
                    <span>{line}</span>
                  </div>
                ))}
          </pre>
        </div>
      </div>
    </div>
  )
}
