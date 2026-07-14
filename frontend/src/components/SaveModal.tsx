import { useState } from 'react'
import type { ElementInspectionResult, LocatorCandidate } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  inspection: ElementInspectionResult | null
  primaryLocator: LocatorCandidate | null
  screenshot?: string | null
  xml?: string | null
  platform: string
  onSave: (data: {
    project_name: string
    feature_name: string
    screen_name: string
    element_name: string
  }) => Promise<void>
}

export default function SaveModal({
  open, onClose, inspection, primaryLocator, onSave,
}: Props) {
  const [project, setProject] = useState('ShoppingApp')
  const [feature, setFeature] = useState('Login')
  const [screen, setScreen] = useState('LoginPage')
  const [elementName, setElementName] = useState('login_button')
  const [saving, setSaving] = useState(false)

  if (!open) return null

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({ project_name: project, feature_name: feature, screen_name: screen, element_name: elementName })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Save Element</h3>
        <div className="form-grid">
          <label>Project<input value={project} onChange={(e) => setProject(e.target.value)} /></label>
          <label>Feature<input value={feature} onChange={(e) => setFeature(e.target.value)} /></label>
          <label>Screen<input value={screen} onChange={(e) => setScreen(e.target.value)} /></label>
          <label>Element<input value={elementName} onChange={(e) => setElementName(e.target.value)} /></label>
        </div>
        {primaryLocator && (
          <div className="primary-locator-preview">
            <strong>Primary Locator:</strong> {primaryLocator.display_name}
            <code className="mono">{primaryLocator.value}</code>
          </div>
        )}
        <div className="modal-actions">
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={handleSave} disabled={saving || !inspection}>
            {saving ? 'Saving...' : 'Save Element'}
          </button>
        </div>
      </div>
    </div>
  )
}
