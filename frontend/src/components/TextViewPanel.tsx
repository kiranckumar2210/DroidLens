import type { ElementInspectionResult, LocatorCandidate } from '../types'

interface Props {
  inspection: ElementInspectionResult | null
  selectedLocator?: LocatorCandidate | null
  onSelectLocator: (loc: LocatorCandidate) => void
  onPreviewLocator?: (loc: LocatorCandidate) => void
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

export default function TextViewPanel({ inspection }: Props) {
  if (!inspection) {
    return <div className="empty-state">Click an element to inspect</div>
  }

  const { element, parent, children, analysis } = inspection
  const bounds = element.bounds
    ? `[${element.bounds.x1},${element.bounds.y1}][${element.bounds.x2},${element.bounds.y2}]`
    : undefined

  return (
    <div className="text-view-content">
      <section className="prop-section">
        <h4>{element.class_name.split('.').pop() || 'Element'}</h4>
        <PropertyRow label="Text" value={element.text} />
        <PropertyRow label="Resource-ID" value={element.resource_id} />
        <PropertyRow label="Class" value={element.class_name} />
        <PropertyRow label="Content-Desc" value={element.content_desc} />
        <PropertyRow label="Package" value={element.package} />
        <PropertyRow label="Bounds" value={bounds} />
        <PropertyRow label="Clickable" value={element.clickable} />
        <PropertyRow label="Enabled" value={element.enabled} />
        <PropertyRow label="Depth" value={String(element.depth)} />
        <PropertyRow label="Index" value={String(element.index)} />
      </section>

      {parent && (
        <section className="prop-section">
          <h4>Parent</h4>
          <PropertyRow label="Class" value={parent.class_name} />
          <PropertyRow label="Text" value={parent.text} />
          <PropertyRow label="Resource-ID" value={parent.resource_id} />
        </section>
      )}

      {children.length > 0 && (
        <section className="prop-section">
          <h4>Children ({children.length})</h4>
          {children.slice(0, 8).map((c) => (
            <PropertyRow
              key={c.id}
              label={c.class_name.split('.').pop() || 'child'}
              value={c.text || c.resource_id || c.content_desc}
            />
          ))}
        </section>
      )}

      {analysis && (
        <section className="prop-section">
          <h4>Hierarchy Context</h4>
          <PropertyRow label="Ancestors" value={String(analysis.ancestor_count)} />
          <PropertyRow label="Siblings" value={String(analysis.sibling_count)} />
          <PropertyRow label="In RecyclerView" value={analysis.is_in_recyclerview} />
          <PropertyRow label="Dynamic text" value={analysis.has_dynamic_text} />
          <PropertyRow label="Stable attrs" value={analysis.stable_attributes.join(', ') || 'none'} />
        </section>
      )}
    </div>
  )
}
