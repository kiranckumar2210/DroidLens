import { lazy, Suspense, useState } from 'react'
import { Settings } from 'lucide-react'
import RecordingActionPanel from './RecordingActionPanel'
import RecordingTimeline from './RecordingTimeline'
import RecordingToolbar from './RecordingToolbar'
import type { ElementInspectionResult, LocatorCandidate } from '../../types'
import type { ExecuteActionPayload, RecordingSettings } from '../../recording/types'
import { LANGUAGE_PROFILES } from '../../recording/types'
import type { useRecording } from '../../recording/useRecording'

const MonacoCodeEditor = lazy(() => import('../MonacoCodeEditor'))

type RecordingHook = ReturnType<typeof useRecording>

interface Props {
  recording: RecordingHook
  theme: 'dark' | 'light' | 'system'
  inspection: ElementInspectionResult | null
  selectedLocator: LocatorCandidate | null
  onNotify: (msg: string, kind?: 'info' | 'success' | 'warning' | 'error') => void
  onDeleteStep?: (stepId: string) => void
  onAfterExecute?: () => void
  /** When true, toolbar is rendered by RecordingModeBar — show action panel + timeline only */
  embedded?: boolean
  onStart?: () => void
  onStop?: () => void
}

export default function RecordingPanel({
  recording, theme, inspection, selectedLocator, onNotify, onDeleteStep, onAfterExecute,
  embedded = false, onStart, onStop,
}: Props) {
  const [showSettings, setShowSettings] = useState(false)
  const [scriptOverride, setScriptOverride] = useState<string | null>(null)

  const {
    session, settings, state, elapsed, isActive, isRecording, executing,
    start, stop, pause, resume, clear, undo, redo,
    copyScript, exportScript, updateSettings, executeAction,
  } = recording

  const steps = session?.steps ?? []
  const script = scriptOverride ?? session?.full_script ?? ''
  const readOnly = isActive

  const handleStart = async () => {
    if (onStart) {
      onStart()
      return
    }
    try {
      await start()
      setScriptOverride(null)
      onNotify('Recording started — select elements and use the Action Panel', 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }

  const handleStop = async () => {
    if (onStop) {
      onStop()
      return
    }
    try {
      const s = await stop()
      setScriptOverride(s?.full_script ?? null)
      onNotify(`Recording stopped — ${s?.steps.length ?? 0} actions captured`, 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }

  const handleExport = async () => {
    try {
      const content = await exportScript()
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `droidlens-recording-${session?.id?.slice(0, 8) ?? 'script'}.py`
      a.click()
      URL.revokeObjectURL(url)
      onNotify('Script exported', 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }

  const patchSettings = (patch: Partial<RecordingSettings>) => {
    void updateSettings(patch).then(() => {
      setScriptOverride(null)
    })
  }

  const handleExecute = async (payload: ExecuteActionPayload) => {
    try {
      await executeAction(payload)
      onAfterExecute?.()
      onNotify(`Recorded: ${payload.action_type.replace(/_/g, ' ')}`, 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }

  return (
    <div className={`recording-panel ${embedded ? 'recording-panel-embedded' : ''}`}>
      {!embedded && (
        <RecordingToolbar
          state={state}
          elapsed={elapsed}
          stepCount={steps.length}
          onStart={handleStart}
          onStop={handleStop}
          onPause={() => void pause()}
          onResume={() => void resume()}
          onClear={() => void clear()}
          onUndo={() => void undo()}
          onRedo={() => void redo()}
          onCopy={() => void copyScript().then(() => onNotify('Script copied', 'success'))}
          onExport={handleExport}
          onSave={() => onNotify('Session saved automatically', 'info')}
        />
      )}

      <div className="recording-panel-toolbar-secondary">
        <select
          value={settings.language_profile}
          onChange={(e) => patchSettings({ language_profile: e.target.value })}
          aria-label="Framework and language"
        >
          {LANGUAGE_PROFILES.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
        <button type="button" className="btn-icon copy-btn" onClick={() => setShowSettings(!showSettings)} title="Settings">
          <Settings size={14} />
        </button>
      </div>

      {showSettings && (
        <div className="recording-settings">
          <label><input type="checkbox" checked={settings.automatic_waits} onChange={(e) => patchSettings({ automatic_waits: e.target.checked })} /> Automatic waits</label>
          <label><input type="checkbox" checked={settings.include_comments} onChange={(e) => patchSettings({ include_comments: e.target.checked })} /> Include comments</label>
          <label><input type="checkbox" checked={settings.mask_passwords} onChange={(e) => patchSettings({ mask_passwords: e.target.checked })} /> Mask passwords</label>
          <label>
            Wait timeout
            <input type="number" min={1} max={60} value={settings.wait_timeout} onChange={(e) => patchSettings({ wait_timeout: Number(e.target.value) })} />
          </label>
          <label>
            Locator strategy
            <select value={settings.preferred_locator_strategy} onChange={(e) => patchSettings({ preferred_locator_strategy: e.target.value })}>
              <option value="auto">Auto (best score)</option>
              <option value="resource_id">Resource ID</option>
              <option value="content_desc">Content Description</option>
              <option value="text">Text</option>
              <option value="uiautomator">UiSelector</option>
            </select>
          </label>
        </div>
      )}

      {!embedded && (
        <RecordingActionPanel
          inspection={inspection}
          selectedLocator={selectedLocator}
          isRecording={isRecording}
          busy={executing}
          onExecute={handleExecute}
        />
      )}

      <div className="recording-panel-body">
        <div className="recording-timeline-pane">
          <h3>Timeline</h3>
          <RecordingTimeline
            steps={steps}
            onDelete={(id) => onDeleteStep?.(id)}
            onToggle={() => { /* server-side toggle future */ }}
          />
        </div>
        <div className="recording-code-pane">
          <h3>Generated Script {readOnly && <span className="readonly-badge">read-only</span>}</h3>
          <Suspense fallback={<div className="monaco-loading">Loading editor…</div>}>
            <MonacoCodeEditor
              value={script}
              onChange={readOnly ? undefined : setScriptOverride}
              language={settings.language_profile}
              theme={theme}
              height={280}
              readOnly={readOnly}
            />
          </Suspense>
        </div>
      </div>
    </div>
  )
}
