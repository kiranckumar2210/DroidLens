import { useState } from 'react'
import type { CustomLocatorResult } from '../types'

interface Props {
  deviceId: string | null
  onBuild: (rules: { attribute: string; operator: string; value: string }[], axis?: string) => Promise<CustomLocatorResult>
  onApply: (result: CustomLocatorResult) => void
}

const ATTRIBUTES = ['resource-id', 'text', 'class', 'content-desc', 'package']
const OPERATORS = ['equals', 'contains', 'starts_with', 'ends_with', 'regex']
const AXES = ['', 'parent', 'child', 'sibling', 'ancestor', 'descendant']

export default function LocatorBuilder({ deviceId, onBuild, onApply }: Props) {
  const [attr, setAttr] = useState('resource-id')
  const [op, setOp] = useState('equals')
  const [value, setValue] = useState('')
  const [axis, setAxis] = useState('')
  const [result, setResult] = useState<CustomLocatorResult | null>(null)
  const [loading, setLoading] = useState(false)

  const build = async () => {
    if (!deviceId || !value.trim()) return
    setLoading(true)
    try {
      const r = await onBuild([{ attribute: attr, operator: op, value: value.trim() }], axis || undefined)
      setResult(r)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel locator-builder-panel">
      <div className="panel-header">Custom Locator Builder</div>
      <div className="builder-body">
        <div className="builder-row">
          <select value={attr} onChange={(e) => setAttr(e.target.value)}>
            {ATTRIBUTES.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <select value={op} onChange={(e) => setOp(e.target.value)}>
            {OPERATORS.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
        <input
          className="full-width"
          placeholder="Value..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <select value={axis} onChange={(e) => setAxis(e.target.value)} className="full-width">
          {AXES.map((a) => (
            <option key={a || 'none'} value={a}>{a ? `Axis: ${a}` : 'No axis'}</option>
          ))}
        </select>
        <button onClick={build} disabled={!deviceId || loading || !value.trim()}>
          {loading ? 'Validating...' : 'Build & Validate'}
        </button>

        {result && (
          <div className="builder-result">
            <div className="match-count">{result.match_count} match(es)</div>
            <div className="mono result-block">{result.uiautomator2}</div>
            <div className="mono result-block">{result.xpath}</div>
            <button onClick={() => onApply(result)}>Use Locator</button>
          </div>
        )}
      </div>
    </div>
  )
}
