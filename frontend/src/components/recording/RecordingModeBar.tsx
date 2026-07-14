import { ChevronDown, ChevronUp, X } from 'lucide-react'
import RecordingActionPanel from './RecordingActionPanel'
import RecordingToolbar from './RecordingToolbar'
import type { ElementInspectionResult, LocatorCandidate } from '../../types'
import type { ExecuteActionPayload } from '../../recording/types'
import type { useRecording } from '../../recording/useRecording'

type RecordingHook = ReturnType<typeof useRecording>

interface Props {
  recording: RecordingHook
  expanded: boolean
  onToggleExpand: () => void
  onClose: () => void
  onStart: () => void
  onStop: () => void
  onNotify: (msg: string, kind?: 'info' | 'success' | 'warning' | 'error') => void
  inspection: ElementInspectionResult | null
  selectedLocator: LocatorCandidate | null
  onExecute: (payload: ExecuteActionPayload) => void
}

export default function RecordingModeBar({
  recording,
  expanded,
  onToggleExpand,
  onClose,
  onStart,
  onStop,
  onNotify,
  inspection,
  selectedLocator,
  onExecute,
}: Props) {
  const { session, state, elapsed, isActive, isRecording, executing } = recording
  const steps = session?.steps ?? []

  return (
    <div className="recording-mode-bar" role="region" aria-label="Recording mode">
      <div className="recording-mode-bar-header">
        <span className="recording-mode-label">Recording Mode</span>
        <RecordingToolbar
          state={state}
          elapsed={elapsed}
          stepCount={steps.length}
          hasScript={Boolean(recording.getLiveScript()?.trim())}
          onStart={onStart}
          onStop={onStop}
          onPause={() => void recording.pause()}
          onResume={() => void recording.resume()}
          onClear={() => void recording.clear()}
          onUndo={() => void recording.undo()}
          onRedo={() => void recording.redo()}
          onCopy={() => void recording.copyScript().then(() => onNotify('Automation script copied to clipboard.', 'success')).catch((e) => onNotify((e as Error).message, 'error'))}
          onExport={() => void recording.downloadScript().then(() => onNotify('Script downloaded', 'success')).catch((e) => onNotify((e as Error).message, 'error'))}
          onSave={() => onNotify('Session saved automatically', 'info')}
        />
        <div className="recording-mode-bar-actions">
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={onToggleExpand}
            title={expanded ? 'Collapse timeline' : 'Expand timeline & code'}
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            {expanded ? 'Collapse' : 'Timeline'}
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={onClose}
            title={isActive ? 'Stop recording and return to inspector' : 'Exit recording mode'}
          >
            <X size={14} />
            {isActive ? 'Stop & Close' : 'Close'}
          </button>
        </div>
      </div>
      <RecordingActionPanel
        inspection={inspection}
        selectedLocator={selectedLocator}
        isRecording={isRecording}
        busy={executing}
        onExecute={onExecute}
      />
    </div>
  )
}
