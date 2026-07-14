import { lazy, Suspense, useMemo } from 'react'
import { Copy, Download } from 'lucide-react'
import RecordingTimeline from './RecordingTimeline'
import { LANGUAGE_PROFILES } from '../../recording/types'
import type { useRecording } from '../../recording/useRecording'
import {
  countScriptLines,
  profileLabel,
  recordingFilename,
} from '../../recording/exportUtils'

const MonacoCodeEditor = lazy(() => import('../MonacoCodeEditor'))

type RecordingHook = ReturnType<typeof useRecording>

interface Props {
  recording: RecordingHook
  theme: 'dark' | 'light' | 'system'
  expanded: boolean
  onNotify: (msg: string, kind?: 'info' | 'success' | 'warning' | 'error') => void
  onDeleteStep?: (stepId: string) => void
}

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

export default function RecordingLivePanel({
  recording,
  theme,
  expanded,
  onNotify,
  onDeleteStep,
}: Props) {
  const {
    session,
    settings,
    state,
    elapsed,
    isActive,
    isRecording,
    updateSettings,
    getLiveScript,
    copyScript,
    downloadScript,
  } = recording

  const steps = session?.steps ?? []
  const script = getLiveScript()
  const lineCount = useMemo(() => countScriptLines(script), [script])

  const handleCopy = async () => {
    try {
      await copyScript()
      onNotify('Automation script copied to clipboard.', 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }

  const handleDownload = async () => {
    try {
      await downloadScript()
      onNotify(`Downloaded ${recordingFilename(settings.language_profile)}`, 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }

  const canExport = script.trim().length > 0

  return (
    <div className={`recording-live-panel ${expanded ? 'expanded' : ''}`}>
      <div className="recording-live-stats">
        <div className="rec-stat">
          <span className="rec-stat-label">Recording time</span>
          <span className="rec-stat-value">{formatElapsed(elapsed)}</span>
        </div>
        <div className="rec-stat">
          <span className="rec-stat-label">Actions</span>
          <span className="rec-stat-value">{steps.length}</span>
        </div>
        <div className="rec-stat">
          <span className="rec-stat-label">Generated lines</span>
          <span className="rec-stat-value">{lineCount}</span>
        </div>
        <div className="rec-stat">
          <span className="rec-stat-label">Framework</span>
          <span className="rec-stat-value rec-stat-framework">{profileLabel(settings.language_profile)}</span>
        </div>
        <div className="rec-stat">
          <span className="rec-stat-label">Locator strategy</span>
          <span className="rec-stat-value">{settings.preferred_locator_strategy}</span>
        </div>
        <div className="rec-stat">
          <span className="rec-stat-label">Status</span>
          <span className={`rec-stat-value rec-status-${state}`}>{state}</span>
        </div>
        <div className="recording-live-actions">
          <select
            value={settings.language_profile}
            onChange={(e) => void updateSettings({ language_profile: e.target.value })}
            aria-label="Framework and language"
            className="rec-lang-select"
          >
            {LANGUAGE_PROFILES.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={!canExport}
            onClick={() => void handleCopy()}
            title="Copy generated script"
          >
            <Copy size={14} /> Copy code
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={!canExport}
            onClick={() => void handleDownload()}
            title="Download script file"
          >
            <Download size={14} /> Download
          </button>
        </div>
      </div>

      <div className="recording-live-body">
        <div className="recording-timeline-pane">
          <h3>Timeline</h3>
          <RecordingTimeline
            steps={steps}
            onDelete={(id) => onDeleteStep?.(id)}
            onToggle={() => { /* server-side toggle future */ }}
          />
        </div>
        <div className="recording-code-pane">
          <h3>
            Live generated code
            {isActive && <span className="readonly-badge">live</span>}
          </h3>
          <Suspense fallback={<div className="monaco-loading">Loading editor…</div>}>
            <MonacoCodeEditor
              value={script || '# Start recording — code appears here after each action\n'}
              language={settings.language_profile}
              theme={theme}
              height={expanded ? 360 : 220}
              readOnly={isRecording}
              scrollToEnd
            />
          </Suspense>
        </div>
      </div>
    </div>
  )
}
