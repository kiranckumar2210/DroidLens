import { Copy } from 'lucide-react'

const ACTIONS = [
  'click', 'long_click', 'double_click', 'set_text', 'clear_text',
  'wait', 'exists', 'assert_exists', 'press_back', 'press_home', 'press_recent',
]

interface Props {
  code: string
  pageObject: string
  framework: string
  action: string
  onFrameworkChange: (f: string) => void
  onActionChange: (a: string) => void
}

export default function CodePanel({
  code, pageObject, framework, action, onFrameworkChange, onActionChange,
}: Props) {
  const full = pageObject ? `${code}\n\n# --- Page Object ---\n${pageObject}` : code

  return (
    <div className="panel code-panel">
      <div className="panel-header">
        <span>Generated Code — Python</span>
        <div className="code-controls">
          <select value={framework} onChange={(e) => onFrameworkChange(e.target.value)}>
            <option value="uiautomator2">uiautomator2</option>
            <option value="appium">Appium</option>
          </select>
          <select value={action} onChange={(e) => onActionChange(e.target.value)}>
            {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <button className="copy-btn" onClick={() => navigator.clipboard.writeText(full)}>
            <Copy size={14} /> Copy
          </button>
        </div>
      </div>
      <pre className="code-block mono">{full || '# Select an element to generate uiautomator2 code'}</pre>
    </div>
  )
}
