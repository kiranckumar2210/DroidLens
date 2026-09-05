import {
  ArrowLeft, Circle, Copy, Download, LayoutGrid, Layers,
  Pause, Play, RotateCcw, Save, Square,
} from 'lucide-react'
import { LANGUAGE_PROFILES } from '../../recording/types'
import type { RecordingState } from '../../recording/types'
import { profileLabel } from '../../recording/exportUtils'

interface Props {
  state: RecordingState
  elapsed: number
  stepCount: number
  deviceName: string
  languageProfile: string
  hasScript: boolean
  onBack: () => void
  onStart: () => void
  onPause: () => void
  onResume: () => void
  onStop: () => void
  onRestart: () => void
  onSave: () => void
  onCopy: () => void
  onDownload: () => void
  onDownloadPageObject: () => void
  onLanguageChange: (profile: string) => void
  onResetLayout: () => void
  onTogglePanel: (panel: 'left' | 'middle' | 'right') => void
}

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

export default function RecordingStudioToolbar({
  state,
  elapsed,
  stepCount,
  deviceName,
  languageProfile,
  hasScript,
  onBack,
  onStart,
  onPause,
  onResume,
  onStop,
  onRestart,
  onSave,
  onCopy,
  onDownload,
  onDownloadPageObject,
  onLanguageChange,
  onResetLayout,
  onTogglePanel,
}: Props) {
  const isRecording = state === 'recording'
  const isPaused = state === 'paused'
  const isActive = isRecording || isPaused

  return (
    <header className="recording-studio-toolbar">
      <div className="rst-left">
        <button type="button" className="btn-secondary btn-sm rst-back" onClick={onBack} title="Back to Live Inspector">
          <ArrowLeft size={16} /> Back
        </button>
        <span className={`rst-rec-indicator ${isRecording ? 'live' : ''}`}>
          {isRecording && <Circle size={10} className="rec-dot" fill="currentColor" />}
          {isRecording ? 'Recording' : isPaused ? 'Paused' : state === 'stopped' ? 'Stopped' : 'Ready'}
        </span>
        <span className="rst-device">{deviceName || 'Device'}</span>
        {isActive && <span className="rst-timer">{formatElapsed(elapsed)}</span>}
        <span className="rst-steps">{stepCount} steps</span>
      </div>

      <div className="rst-center">
        <select
          value={languageProfile}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="rst-lang-select"
          aria-label="Framework and language"
        >
          {LANGUAGE_PROFILES.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
        <span className="rst-framework-label">{profileLabel(languageProfile)}</span>
      </div>

      <div className="rst-actions">
        {!isActive && (
          <button type="button" className="btn-primary btn-sm" onClick={onStart}>
            <Play size={14} /> Start
          </button>
        )}
        {isRecording && (
          <button type="button" className="btn-secondary btn-sm" onClick={onPause}>
            <Pause size={14} /> Pause
          </button>
        )}
        {isPaused && (
          <button type="button" className="btn-primary btn-sm" onClick={onResume}>
            <Play size={14} /> Resume
          </button>
        )}
        {isActive && (
          <button type="button" className="btn-secondary btn-sm rec-stop" onClick={onStop}>
            <Square size={14} /> Stop
          </button>
        )}
        <button type="button" className="btn-secondary btn-sm" onClick={onRestart} title="Restart recording">
          <RotateCcw size={14} /> Restart
        </button>
        <button type="button" className="btn-icon copy-btn" onClick={onSave} title="Save session">
          <Save size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled={!hasScript} onClick={onCopy} title="Copy code">
          <Copy size={14} />
        </button>
        <button type="button" className="btn-icon copy-btn" disabled={!hasScript} onClick={onDownload} title="Download script">
          <Download size={14} />
        </button>
        <button type="button" className="btn-secondary btn-sm" disabled={!hasScript} onClick={onDownloadPageObject} title="Export Page Object + test">
          <Layers size={14} /> POM
        </button>
        <div className="rst-layout-group">
          <button type="button" className="btn-icon copy-btn" onClick={() => onTogglePanel('left')} title="Toggle screenshot panel">L</button>
          <button type="button" className="btn-icon copy-btn" onClick={() => onTogglePanel('middle')} title="Toggle actions panel">M</button>
          <button type="button" className="btn-icon copy-btn" onClick={() => onTogglePanel('right')} title="Toggle code panel">R</button>
          <button type="button" className="btn-icon copy-btn" onClick={onResetLayout} title="Reset layout">
            <LayoutGrid size={14} />
          </button>
        </div>
      </div>
    </header>
  )
}
