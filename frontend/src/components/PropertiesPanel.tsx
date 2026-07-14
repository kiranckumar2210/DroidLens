import { Copy, Star } from 'lucide-react'
import type { ElementInspectionResult, LocatorCandidate } from '../types'

interface Props {
  inspection: ElementInspectionResult | null
  onSelectLocator: (loc: LocatorCandidate) => void
  selectedLocator?: LocatorCandidate | null
}

function scoreClass(score: number) {
  if (score >= 0.75) return 'high'
  if (score >= 0.5) return 'mid'
  return 'low'
}

function PropertyRow({ label, value }: { label: string; value?: string | null | boolean }) {
  if (value === undefined || value === null || value === '') return null
  return (
    <div className="prop-row">
      <span className="prop-label">{label}</span>
      <span className="prop-value mono">{String(value)}</span>
    </div>
  )
}

export default function PropertiesPanel({ inspection, onSelectLocator, selectedLocator }: Props) {
  if (!inspection) {
    return (
      <div className="panel properties-panel">
        <div className="panel-header">Properties & Locators</div>
        <div className="empty-state">Click an element to inspect</div>
      </div>
    )
  }

  const { element, parent, locators, xpath_examples } = inspection
  const bounds = element.bounds
    ? `[${element.bounds.x1},${element.bounds.y1}][${element.bounds.x2},${element.bounds.y2}]`
    : undefined

  const copy = (text: string) => navigator.clipboard.writeText(text)

  return (
    <div className="panel properties-panel">
      <div className="panel-header">
        {element.class_name.split('.').pop() || 'Element'}
      </div>
      <div className="properties-scroll">
        <section className="prop-section">
          <h4>Properties</h4>
          <PropertyRow label="Type" value={element.class_name.split('.').pop()} />
          <PropertyRow label="Class" value={element.class_name} />
          <PropertyRow label="Text" value={element.text} />
          <PropertyRow label="Resource-ID" value={element.resource_id} />
          <PropertyRow label="Accessibility ID" value={element.accessibility_id} />
          <PropertyRow label="Content-Desc" value={element.content_desc} />
          <PropertyRow label="Hint" value={element.hint} />
          <PropertyRow label="Package" value={element.package} />
          <PropertyRow label="Bounds" value={bounds} />
          <PropertyRow label="Index" value={String(element.index)} />
          <PropertyRow label="Instance" value={String(element.instance)} />
          <PropertyRow label="Depth" value={String(element.depth)} />
          <PropertyRow label="Drawing Order" value={element.drawing_order != null ? String(element.drawing_order) : undefined} />
          <PropertyRow label="Enabled" value={element.enabled} />
          <PropertyRow label="Visible" value={element.visible} />
          <PropertyRow label="Clickable" value={element.clickable} />
          <PropertyRow label="Long-Clickable" value={element.long_clickable} />
          <PropertyRow label="Scrollable" value={element.scrollable} />
          <PropertyRow label="Focusable" value={element.focusable} />
          <PropertyRow label="Focused" value={element.focused} />
          <PropertyRow label="Checkable" value={element.checkable} />
          <PropertyRow label="Checked" value={element.checked} />
          <PropertyRow label="Selected" value={element.selected} />
          <PropertyRow label="Password" value={element.password} />
          {element.is_flutter && (
            <>
              <PropertyRow label="Flutter" value="Yes" />
              <PropertyRow label="Semantics" value={element.flutter_semantics} />
            </>
          )}
        </section>

        {parent && (
          <section className="prop-section">
            <h4>Parent</h4>
            <PropertyRow label="Class" value={parent.class_name} />
          </section>
        )}

        <section className="prop-section">
          <h4>Locator Suggestions</h4>
          {locators.map((loc, i) => (
            <div
              key={`${loc.locator_type}-${i}`}
              className={`locator-card ${selectedLocator?.value === loc.value ? 'active' : ''}`}
              onClick={() => onSelectLocator(loc)}
            >
              <div className="locator-header">
                <span className="locator-name">
                  {i === 0 && <Star size={12} className="star-icon" />}
                  {loc.display_name}
                </span>
                <span className={`badge ${loc.recommended ? 'recommended' : loc.scores.overall < 0.5 ? 'avoid' : 'neutral'}`}>
                  {Math.round(loc.scores.overall * 100)}%
                </span>
              </div>
              <div className="locator-value mono">{loc.value}</div>
              <div className="score-bar">
                <div
                  className={`score-bar-fill ${scoreClass(loc.scores.overall)}`}
                  style={{ width: `${loc.scores.overall * 100}%` }}
                />
              </div>
              <div className="locator-meta">
                <span>S:{Math.round(loc.scores.stability * 100)} U:{Math.round(loc.scores.uniqueness * 100)} M:{Math.round(loc.scores.maintainability * 100)}</span>
                <button className="copy-btn" onClick={(e) => { e.stopPropagation(); copy(loc.value) }}>
                  <Copy size={12} />
                </button>
              </div>
              <p className="locator-reason">{loc.reason}</p>
            </div>
          ))}
        </section>

        {xpath_examples.length > 0 && (
          <section className="prop-section">
            <h4>XPath Builder</h4>
            {xpath_examples.slice(0, 8).map((ex, i) => (
              <div key={i} className="xpath-example">
                <span className="xpath-axis">{ex.axis}</span>
                <code className="mono">{ex.xpath}</code>
                <button className="copy-btn" onClick={() => copy(ex.xpath)}>
                  <Copy size={12} />
                </button>
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
