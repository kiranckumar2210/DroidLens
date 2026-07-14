import { useState } from 'react'
import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUp,
  CheckCircle, Home, Keyboard, MousePointer, RotateCcw,
  Smartphone, Type, Undo2,
} from 'lucide-react'
import type { ElementInspectionResult, LocatorCandidate } from '../../types'
import type { ExecuteActionPayload } from '../../recording/types'
import type { RecordedActionType } from '../../recording/types'

export type { ExecuteActionPayload }

interface Props {
  inspection: ElementInspectionResult | null
  selectedLocator: LocatorCandidate | null
  isRecording: boolean
  busy: boolean
  onExecute: (payload: ExecuteActionPayload) => Promise<void>
}

function ActionBtn({
  label, icon, onClick, disabled, title,
}: {
  label: string
  icon: React.ReactNode
  onClick: () => void
  disabled?: boolean
  title?: string
}) {
  return (
    <button
      type="button"
      className="rec-action-btn"
      onClick={onClick}
      disabled={disabled}
      title={title || label}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

export default function RecordingActionPanel({
  inspection,
  selectedLocator,
  isRecording,
  busy,
  onExecute,
}: Props) {
  const [textInput, setTextInput] = useState('')
  const [showTextInput, setShowTextInput] = useState(false)

  if (!isRecording) return null

  const elementId = inspection?.element?.id
  const hasElement = Boolean(elementId)
  const disabled = busy

  const run = (action_type: RecordedActionType, extra: Partial<ExecuteActionPayload> = {}) => {
    void onExecute({
      action_type,
      element_id: elementId,
      locator_type: selectedLocator?.locator_type,
      locator_value: selectedLocator?.value,
      ...extra,
    })
  }

  const runDevice = (action_type: RecordedActionType) => {
    void onExecute({ action_type })
  }

  const el = inspection?.element
  const elLabel = el?.resource_id?.split('/').pop() || el?.text || el?.class_name?.split('.').pop() || 'No element selected'

  return (
    <div className="recording-action-panel">
      <div className="rec-action-header">
        <MousePointer size={14} />
        <div>
          <strong>Record Action</strong>
          <span className="rec-action-target">{elLabel}</span>
        </div>
      </div>

      {!hasElement && (
        <p className="rec-action-hint">Select an element from the screenshot or hierarchy, then choose an action.</p>
      )}

      <div className="rec-action-section">
        <h4>Touch</h4>
        <div className="rec-action-grid">
          <ActionBtn label="Click" icon={<MousePointer size={14} />} disabled={disabled || !hasElement} onClick={() => run('tap')} />
          <ActionBtn label="Double Click" icon={<MousePointer size={14} />} disabled={disabled || !hasElement} onClick={() => run('double_tap')} />
          <ActionBtn label="Long Press" icon={<MousePointer size={14} />} disabled={disabled || !hasElement} onClick={() => run('long_press')} />
        </div>
      </div>

      <div className="rec-action-section">
        <h4>Text</h4>
        {showTextInput ? (
          <div className="rec-text-input-row">
            <input
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Text to enter…"
              aria-label="Text to enter"
            />
            <button type="button" className="btn-sm btn-primary" disabled={disabled || !hasElement} onClick={() => { run('set_text', { text_value: textInput }); setShowTextInput(false) }}>
              Send
            </button>
            <button type="button" className="btn-sm btn-secondary" onClick={() => setShowTextInput(false)}>Cancel</button>
          </div>
        ) : (
          <div className="rec-action-grid">
            <ActionBtn label="Enter Text" icon={<Type size={14} />} disabled={disabled || !hasElement} onClick={() => setShowTextInput(true)} />
            <ActionBtn label="Clear Text" icon={<Keyboard size={14} />} disabled={disabled || !hasElement} onClick={() => run('clear_text')} />
          </div>
        )}
      </div>

      <div className="rec-action-section">
        <h4>Gestures</h4>
        <div className="rec-action-grid">
          <ActionBtn label="Swipe Up" icon={<ArrowUp size={14} />} disabled={disabled || !hasElement} onClick={() => run('scroll', { swipe_direction: 'up' })} />
          <ActionBtn label="Swipe Down" icon={<ArrowDown size={14} />} disabled={disabled || !hasElement} onClick={() => run('scroll', { swipe_direction: 'down' })} />
          <ActionBtn label="Swipe Left" icon={<ArrowLeft size={14} />} disabled={disabled || !hasElement} onClick={() => run('swipe', { swipe_direction: 'left' })} />
          <ActionBtn label="Swipe Right" icon={<ArrowRight size={14} />} disabled={disabled || !hasElement} onClick={() => run('swipe', { swipe_direction: 'right' })} />
        </div>
      </div>

      <div className="rec-action-section">
        <h4>Waits</h4>
        <div className="rec-action-grid">
          <ActionBtn label="Wait Visible" icon={<RotateCcw size={14} />} disabled={disabled || !hasElement} onClick={() => run('wait_visible')} />
          <ActionBtn label="Wait Clickable" icon={<RotateCcw size={14} />} disabled={disabled || !hasElement} onClick={() => run('wait_clickable')} />
          <ActionBtn label="Wait Gone" icon={<RotateCcw size={14} />} disabled={disabled || !hasElement} onClick={() => run('wait_gone')} />
        </div>
      </div>

      <div className="rec-action-section">
        <h4>Validation</h4>
        <div className="rec-action-grid">
          <ActionBtn label="Verify Exists" icon={<CheckCircle size={14} />} disabled={disabled || !hasElement} onClick={() => run('verify_exists')} />
          <ActionBtn label="Verify Visible" icon={<CheckCircle size={14} />} disabled={disabled || !hasElement} onClick={() => run('verify_visible')} />
          <ActionBtn label="Verify Enabled" icon={<CheckCircle size={14} />} disabled={disabled || !hasElement} onClick={() => run('verify_enabled')} />
          <ActionBtn label="Verify Text" icon={<CheckCircle size={14} />} disabled={disabled || !hasElement} onClick={() => run('verify_text', { text_value: el?.text || textInput })} />
        </div>
      </div>

      <div className="rec-action-section">
        <h4>Device</h4>
        <div className="rec-action-grid">
          <ActionBtn label="Back" icon={<Undo2 size={14} />} disabled={disabled} onClick={() => runDevice('press_back')} />
          <ActionBtn label="Home" icon={<Home size={14} />} disabled={disabled} onClick={() => runDevice('press_home')} />
          <ActionBtn label="Recent" icon={<Smartphone size={14} />} disabled={disabled} onClick={() => runDevice('press_recent')} />
          <ActionBtn label="Notifications" icon={<Smartphone size={14} />} disabled={disabled} onClick={() => runDevice('open_notification')} />
        </div>
      </div>
    </div>
  )
}
