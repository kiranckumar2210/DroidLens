import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import ScreenshotPanel from '../ScreenshotPanel'
import {
  DEFAULT_STUDIO_LAYOUT,
  resetStudioLayout,
  togglePanelCollapse,
  TripleSplitPane,
  type StudioLayout,
} from '../ui/TripleSplitPane'
import RecordingActionPanel from './RecordingActionPanel'
import RecordingStudioToolbar from './RecordingStudioToolbar'
import RecordingTimeline from './RecordingTimeline'
import type { ElementInspectionResult, ElementNode, InspectionSession, LocatorCandidate } from '../../types'
import type { DeviceInfo } from '../../types'
import type { ExecuteActionPayload, RecordedStep } from '../../recording/types'
import type { useRecording } from '../../recording/useRecording'
import { loadStudioLayout, saveStudioLayout } from '../../recording/storage'
import { profileLabel, countScriptLines, recordingFilename } from '../../recording/exportUtils'

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const MonacoCodeEditor = lazy(() => import('../MonacoCodeEditor'))

type RecordingHook = ReturnType<typeof useRecording>

interface Props {
  recording: RecordingHook
  theme: 'dark' | 'light' | 'system'
  resolvedTheme: 'dark' | 'light'
  session: InspectionSession | null
  inspection: ElementInspectionResult | null
  selectedLocator: LocatorCandidate | null
  device: DeviceInfo | null
  packageName: string
  activity: string
  onSelectAt: (x: number, y: number) => Promise<void>
  onSelectById: (id: string) => Promise<void>
  onRefreshSession: () => Promise<void>
  onBack: () => void
  onNotify: (msg: string, kind?: 'info' | 'success' | 'warning' | 'error') => void
  onExecute: (payload: ExecuteActionPayload) => Promise<void>
  onStart: () => void
  onStop: () => void
}

function stepElementId(step: RecordedStep): string | null {
  const el = step.element as { id?: string } | null | undefined
  return el?.id ?? null
}

function findStepLine(script: string, step: RecordedStep): number | null {
  const snippet = step.code_snippet?.trim()
  if (!snippet) return null
  const needle = snippet.split('\n').find((l) => l.trim())?.trim()
  if (!needle) return null
  const lines = script.split('\n')
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes(needle)) return i + 1
  }
  return null
}

function formatBounds(bounds: ElementNode['bounds']): string {
  if (!bounds) return '—'
  if (Array.isArray(bounds)) return bounds.join(', ')
  const b = bounds as { x1?: number; y1?: number; x2?: number; y2?: number }
  if (b.x1 != null) return `${b.x1}, ${b.y1}, ${b.x2}, ${b.y2}`
  return '—'
}

function findStepForElement(steps: RecordedStep[], elementId: string | undefined): RecordedStep | null {
  if (!elementId) return null
  for (let i = steps.length - 1; i >= 0; i--) {
    if (stepElementId(steps[i]) === elementId) return steps[i]
  }
  return null
}

export default function RecordingStudio({
  recording,
  theme,
  session,
  inspection,
  selectedLocator,
  device,
  packageName,
  activity,
  onSelectAt,
  onSelectById,
  onRefreshSession,
  onBack,
  onNotify,
  onExecute,
  onStart,
  onStop,
}: Props) {
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null)
  const [scrollToLine, setScrollToLine] = useState<number | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [layout, setLayout] = useState<StudioLayout>(() => loadStudioLayout())

  const {
    session: recSession,
    settings,
    state,
    elapsed,
    isRecording,
    isActive,
    executing,
    getLiveScript,
    copyScript,
    downloadScript,
    updateSettings,
    clear,
    pause,
    resume,
    deleteStep,
    reorderSteps,
    toggleStep,
    updateStepComment,
  } = recording

  const steps = recSession?.steps ?? []
  const script = getLiveScript()
  const lineCount = useMemo(() => countScriptLines(script), [script])

  useEffect(() => {
    saveStudioLayout(layout)
  }, [layout])

  // Clicking Record implies intent to capture — auto-start when studio opens fresh.
  useEffect(() => {
    if (!isActive && steps.length === 0 && (state === 'ready' || state === 'stopped')) {
      onStart()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once when studio mounts
  }, [])

  useEffect(() => {
    if (isRecording) {
      setSelectedStepId(null)
      setScrollToLine(null)
    }
  }, [steps.length, isRecording])

  const highlightIds = useMemo(() => {
    if (selectedStepId) {
      const step = steps.find((s) => s.id === selectedStepId)
      const eid = step ? stepElementId(step) : null
      if (eid) return [eid]
    }
    return inspection?.element?.id ? [inspection.element.id] : []
  }, [selectedStepId, steps, inspection])

  const selectedElement = useMemo((): ElementNode | null => {
    if (selectedStepId) {
      const step = steps.find((s) => s.id === selectedStepId)
      if (step?.element) return step.element as ElementNode
    }
    return inspection?.element ?? null
  }, [selectedStepId, steps, inspection])

  const syncToStep = useCallback((stepId: string) => {
    setSelectedStepId(stepId)
    const step = steps.find((s) => s.id === stepId)
    const eid = step ? stepElementId(step) : null
    if (eid) void onSelectById(eid)
    if (step) {
      const line = findStepLine(script, step)
      if (line) setScrollToLine(line)
    }
  }, [steps, onSelectById, script])

  const handleScreenshotSelect = useCallback(async (x: number, y: number) => {
    await onSelectAt(x, y)
  }, [onSelectAt])

  useEffect(() => {
    if (selectedStepId || isRecording) return
    const elId = inspection?.element?.id
    const match = findStepForElement(steps, elId)
    if (match) syncToStep(match.id)
  }, [inspection?.element?.id, steps, selectedStepId, isRecording, syncToStep])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await onRefreshSession()
      onNotify('Screenshot refreshed', 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    } finally {
      setRefreshing(false)
    }
  }, [onRefreshSession, onNotify])

  const handleRestart = useCallback(async () => {
    if (!window.confirm('Restart recording? All recorded steps will be removed.')) return
    try {
      await clear()
      setSelectedStepId(null)
      onNotify('Recording restarted', 'info')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }, [clear, onNotify])

  const handleCopy = useCallback(async () => {
    try {
      await copyScript()
      onNotify('Automation script copied to clipboard.', 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }, [copyScript, onNotify])

  const handleDownload = useCallback(async () => {
    try {
      await downloadScript()
      onNotify(`Downloaded ${recordingFilename(settings.language_profile)}`, 'success')
    } catch (e) {
      onNotify((e as Error).message, 'error')
    }
  }, [downloadScript, settings.language_profile, onNotify])

  const handleMoveStep = useCallback((stepId: string, direction: 'up' | 'down') => {
    const ids = steps.map((s) => s.id)
    const idx = ids.indexOf(stepId)
    if (idx < 0) return
    const swap = direction === 'up' ? idx - 1 : idx + 1
    if (swap < 0 || swap >= ids.length) return
    ;[ids[idx], ids[swap]] = [ids[swap], ids[idx]]
    void reorderSteps(ids).catch((e) => onNotify((e as Error).message, 'error'))
  }, [steps, reorderSteps, onNotify])

  return (
    <div className="recording-studio" role="dialog" aria-label="Recording Studio">
      <RecordingStudioToolbar
        state={state}
        elapsed={elapsed}
        stepCount={steps.length}
        deviceName={device?.model || device?.id || session?.device_id || ''}
        languageProfile={settings.language_profile}
        hasScript={script.trim().length > 0}
        onBack={onBack}
        onStart={onStart}
        onPause={() => void pause()}
        onResume={() => void resume()}
        onStop={onStop}
        onRestart={() => void handleRestart()}
        onSave={() => onNotify('Session saved automatically', 'info')}
        onCopy={() => void handleCopy()}
        onDownload={() => void handleDownload()}
        onLanguageChange={(p) => void updateSettings({ language_profile: p })}
        onResetLayout={() => setLayout(resetStudioLayout())}
        onTogglePanel={(panel) => setLayout((l) => togglePanelCollapse(l, panel))}
      />

      <div className="recording-studio-main">
        <TripleSplitPane layout={layout} onLayoutChange={setLayout}>
          {/* Left — Live Screenshot */}
          <div className="studio-pane studio-pane-screenshot">
            <div className="rst-panel-header">
              <span>Live Screenshot</span>
              <div className="rst-panel-meta">
                <span>{session?.screen_width ?? '—'}×{session?.screen_height ?? '—'}</span>
                <button
                  type="button"
                  className={`btn-icon copy-btn ${refreshing ? 'loading' : ''}`}
                  onClick={() => void handleRefresh()}
                  title="Refresh screenshot"
                >
                  <RefreshCw size={14} />
                </button>
              </div>
            </div>
            <div className="studio-screenshot-body">
              <ScreenshotPanel
                screenshot={session?.screenshot_base64}
                screenshotWidth={
                  session?.coordinate_mapping?.screenshot_width
                  || session?.screenshot_width
                  || session?.screen_width
                  || 1080
                }
                screenshotHeight={
                  session?.coordinate_mapping?.screenshot_height
                  || session?.screenshot_height
                  || session?.screen_height
                  || 1920
                }
                hierarchyWidth={
                  session?.coordinate_mapping?.hierarchy_width
                  || session?.screen_width
                  || 1080
                }
                hierarchyHeight={
                  session?.coordinate_mapping?.hierarchy_height
                  || session?.screen_height
                  || 1920
                }
                tree={session?.tree}
                selectedElement={selectedElement}
                highlightIds={highlightIds}
                onClickCoords={(x, y) => void handleScreenshotSelect(x, y)}
                compactHeader
              />
            </div>
            {selectedElement && (
              <div className="recording-studio-element-tip">
                {selectedElement.resource_id && <span><strong>ID</strong> {selectedElement.resource_id}</span>}
                {selectedElement.content_desc && <span><strong>Desc</strong> {selectedElement.content_desc}</span>}
                {selectedElement.text && <span><strong>Text</strong> {selectedElement.text}</span>}
                <span><strong>Class</strong> {selectedElement.class_name?.split('.').pop() ?? '—'}</span>
                <span><strong>Bounds</strong> [{formatBounds(selectedElement.bounds)}]</span>
              </div>
            )}
            {(packageName || activity) && (
              <div className="studio-package-bar">
                {packageName && <span><strong>Package</strong> {packageName}</span>}
                {activity && <span><strong>Activity</strong> {activity}</span>}
              </div>
            )}
          </div>

          {/* Middle — Recorded Actions */}
          <div className="studio-pane studio-pane-actions">
            <div className="rst-panel-header">
              <span>Recorded Actions</span>
              <span className="rst-timeline-count">{steps.length}</span>
            </div>
            <RecordingTimeline
              steps={steps}
              selectedId={selectedStepId}
              onSelect={syncToStep}
              onDelete={(id) => void deleteStep(id).catch((e) => onNotify((e as Error).message, 'error'))}
              onToggle={(id, enabled) => void toggleStep(id, enabled).catch((e) => onNotify((e as Error).message, 'error'))}
              onMoveUp={(id) => handleMoveStep(id, 'up')}
              onMoveDown={(id) => handleMoveStep(id, 'down')}
              onComment={(id, comment) => void updateStepComment(id, comment).catch((e) => onNotify((e as Error).message, 'error'))}
            />
            <RecordingActionPanel
              inspection={inspection}
              selectedLocator={selectedLocator}
              isRecording={isRecording}
              busy={executing}
              onExecute={onExecute}
            />
          </div>

          {/* Right — Generated Code */}
          <div className="studio-pane studio-pane-code">
            <div className="rst-panel-header">
              <span>Generated Automation Code</span>
              {isActive && <span className="readonly-badge">live</span>}
            </div>
            <Suspense fallback={<div className="monaco-loading">Loading editor…</div>}>
              <MonacoCodeEditor
                value={script || '# Press Start, then record actions — production-ready code appears here\n'}
                language={settings.language_profile}
                theme={theme}
                height="100%"
                readOnly={isRecording}
                scrollToEnd={!selectedStepId}
                scrollToLine={scrollToLine}
              />
            </Suspense>
          </div>
        </TripleSplitPane>
      </div>

      <footer className="recording-studio-statusbar">
        <span>Time: <strong>{formatElapsed(elapsed)}</strong></span>
        <span>Actions: <strong>{steps.length}</strong></span>
        <span>Lines: <strong>{lineCount}</strong></span>
        <span>Framework: <strong>{profileLabel(settings.language_profile)}</strong></span>
        <span>Locator: <strong>{settings.preferred_locator_strategy}</strong></span>
        <span>Device: <strong>{device?.model || device?.id || '—'}</strong></span>
        {recSession?.id && <span>Session: <strong>{recSession.id.slice(0, 8)}</strong></span>}
        <span>Resolution: <strong>{session?.screen_width ?? '—'}×{session?.screen_height ?? '—'}</strong></span>
        {session?.last_refresh_ms != null && (
          <span>Refresh: <strong>{session.last_refresh_ms}ms</strong></span>
        )}
      </footer>
    </div>
  )
}
