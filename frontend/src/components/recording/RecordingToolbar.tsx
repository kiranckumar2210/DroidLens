import {
  Circle, Copy, Download, Pause, Play, Redo2, RotateCcw, Save, Square, Trash2, Undo2,
} from 'lucide-react'
import type { RecordingState } from '../../recording/types'

interface Props {
  state: RecordingState
  elapsed: number
  stepCount: number
  hasScript?: boolean
  onStart: () => void
  onStop: () => void
  onPause: () => void
  onResume: () => void
  onClear: () => void
  onUndo: () => void
  onRedo: () => void
  onCopy: () => void
  onExport: () => void
  onSave: () => void
  disabled?: boolean
}

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

const STATE_LABELS: Record<RecordingState, string> = {
  ready: 'Ready',
  recording: 'Recording',
  paused: 'Paused',
  stopped: 'Stopped',
  saving: 'Saving',
  exported: 'Exported',
}

export default function RecordingToolbar({
  state, elapsed, stepCount, hasScript = false,
  onStart, onStop, onPause, onResume, onClear,
  onUndo, onRedo, onCopy, onExport, onSave,
  disabled,
}: Props) {
  const isRecording = state === 'recording'
  const isPaused = state === 'paused'
  const isActive = isRecording || isPaused
  const canEdit = state === 'stopped' || state === 'ready'

  const canCopy = hasScript || stepCount > 0

  return (
    <div className="recording-toolbar">
      <div className="recording-toolbar-left">
        <span className={`recording-state-pill ${state}`}>
          {isRecording && <Circle size={10} className="rec-dot" fill="currentColor" />}
          {STATE_LABELS[state]}
        </span>
        {isActive && <span className="recording-timer">{formatElapsed(elapsed)}</span>}
        <span className="recording-step-count">{stepCount} steps</span>
      </div>
      <div className="recording-toolbar-actions">
        {!isActive && (
          <button type="button" className="btn-primary btn-sm" disabled={disabled} onClick={onStart} title="Start Recording">
            <Play size={14} /> Record
          </button>
        )}
        {isRecording && (
          <button type="button" className="btn-secondary btn-sm" onClick={onPause} title="Pause">
            <Pause size={14} /> Pause
          </button>
        )}
        {isPaused && (
          <button type="button" className="btn-primary btn-sm" onClick={onResume} title="Resume">
            <Play size={14} /> Resume
          </button>
        )}
        {isActive && (
          <button type="button" className="btn-secondary btn-sm rec-stop" onClick={onStop} title="Stop Recording">
            <Square size={14} /> Stop
          </button>
        )}
        <button type="button" className="btn-icon copy-btn" disabled={!stepCount} onClick={onClear} title="Clear">
          <Trash2 size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled={!stepCount} onClick={onUndo} title="Undo">
          <Undo2 size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled={!stepCount} onClick={onRedo} title="Redo">
          <Redo2 size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled={!canCopy} onClick={onCopy} title="Copy Script">
          <Copy size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled={!canCopy} onClick={onExport} title="Export Script">
          <Download size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled={!canEdit && !stepCount} onClick={onSave} title="Save Session">
          <Save size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled title="Replay (coming soon)">
          <RotateCcw size={14} />
        </button>
      </div>
    </div>
  )
}
