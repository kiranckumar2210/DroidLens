import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { withTimeout } from '../utils/withTimeout'
import {
  copyToClipboard,
  downloadTextFile,
  recordingFilename,
} from './exportUtils'
import {
  loadActiveRecordingSessionId,
  loadRecordingSettings,
  saveActiveRecordingSessionId,
  saveRecordingSettings,
} from './storage'
import type { ExecuteActionPayload, RecordedActionType, RecordingSession, RecordingSettings, RecordingState } from './types'

export function useRecording(deviceId: string | null, packageName: string) {
  const [session, setSession] = useState<RecordingSession | null>(null)
  const [settings, setSettings] = useState<RecordingSettings>(() => {
    const s = loadRecordingSettings()
    return { ...s, package_name: packageName || s.package_name }
  })
  const [error, setError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [executing, setExecuting] = useState(false)
  const timerRef = useRef<number | null>(null)

  const refresh = useCallback(async (sessionId: string) => {
    const s = await api.getRecording(sessionId)
    setSession(s)
    return s
  }, [])

  useEffect(() => {
    const sid = loadActiveRecordingSessionId()
    if (sid && deviceId) {
      withTimeout(api.getRecording(sid), 8000, 'Load recording session')
        .then((s) => {
          if (s.device_id === deviceId) setSession(s)
          else saveActiveRecordingSessionId(null)
        })
        .catch(() => saveActiveRecordingSessionId(null))
    }
  }, [deviceId])

  useEffect(() => {
    if (session?.state === 'recording' && session.started_at) {
      const tick = () => {
        const start = new Date(session.started_at!).getTime()
        setElapsed(Math.floor((Date.now() - start) / 1000))
      }
      tick()
      timerRef.current = window.setInterval(tick, 1000)
      return () => { if (timerRef.current) clearInterval(timerRef.current) }
    }
    if (timerRef.current) clearInterval(timerRef.current)
    return undefined
  }, [session?.state, session?.started_at])

  const getLiveScript = useCallback((): string => {
    const full = session?.full_script?.trim() ?? ''
    const stepsCode = (session?.steps ?? [])
      .filter((s) => s.enabled !== false)
      .map((s) => s.code_snippet)
      .filter(Boolean)
      .join('\n\n')

    if (full && stepsCode) {
      const firstStepLine = stepsCode.split('\n').find((l) => l.trim() && !l.trim().startsWith('#'))?.trim()
      if (!firstStepLine || full.includes(firstStepLine.slice(0, 24))) {
        return full
      }
    }
    if (full && !stepsCode) return full
    if (stepsCode && full) {
      const footerIdx = full.indexOf('# End of recorded')
      const header = footerIdx > 0 ? full.slice(0, footerIdx).split('\n\n')[0] : full.split('\n\n')[0]
      return `${header}\n\n${stepsCode}\n`
    }
    return stepsCode || full
  }, [session])

  const start = useCallback(async () => {
    if (!deviceId) throw new Error('No device connected')
    setError(null)
    const merged = { ...settings, package_name: packageName || settings.package_name }
    const s = await api.startRecording(deviceId, merged)
    setSession(s)
    saveActiveRecordingSessionId(s.id)
    saveRecordingSettings(merged)
    setSettings(merged)
    return s
  }, [deviceId, packageName, settings])

  const stop = useCallback(async () => {
    if (!session) return null
    const s = await api.stopRecording(session.id)
    setSession(s)
    return s
  }, [session])

  const pause = useCallback(async () => {
    if (!session) return
    const s = await api.pauseRecording(session.id)
    setSession(s)
  }, [session])

  const resume = useCallback(async () => {
    if (!session) return
    const s = await api.resumeRecording(session.id)
    setSession(s)
  }, [session])

  const clear = useCallback(async () => {
    if (!session) return
    const s = await api.clearRecording(session.id)
    setSession(s)
  }, [session])

  const undo = useCallback(async () => {
    if (!session) return
    const s = await api.undoRecording(session.id)
    setSession(s)
  }, [session])

  const redo = useCallback(async () => {
    if (!session) return
    const s = await api.redoRecording(session.id)
    setSession(s)
  }, [session])

  const executeAction = useCallback(async (payload: ExecuteActionPayload) => {
    if (!session || session.state !== 'recording') {
      throw new Error('Start recording before executing actions — click Start in the toolbar')
    }
    setExecuting(true)
    setError(null)
    try {
      const s = await api.executeRecordingAction(session.id, payload)
      setSession(s)
      return s
    } catch (e) {
      const msg = (e as Error).message
      if (msg.includes('not found') || msg.includes('404')) {
        saveActiveRecordingSessionId(null)
        setSession(null)
        throw new Error('Recording session expired — click Start to begin a new recording')
      }
      throw e
    } finally {
      setExecuting(false)
    }
  }, [session])

  const deleteStep = useCallback(async (stepId: string) => {
    if (!session) return
    const s = await api.deleteRecordingStep(session.id, stepId)
    setSession(s)
    return s
  }, [session])

  const reorderSteps = useCallback(async (stepIds: string[]) => {
    if (!session) return
    const s = await api.reorderRecordingSteps(session.id, stepIds)
    setSession(s)
    return s
  }, [session])

  const toggleStep = useCallback(async (stepId: string, enabled: boolean) => {
    if (!session) return
    const s = await api.updateRecordingStep(session.id, stepId, { enabled })
    setSession(s)
    return s
  }, [session])

  const updateStepComment = useCallback(async (stepId: string, comment: string) => {
    if (!session) return
    const s = await api.updateRecordingStep(session.id, stepId, { comment })
    setSession(s)
    return s
  }, [session])

  const updateSettings = useCallback(async (patch: Partial<RecordingSettings>) => {
    const merged = { ...settings, ...patch }
    setSettings(merged)
    saveRecordingSettings(merged)
    if (session) {
      const s = await api.updateRecordingSettings(session.id, merged)
      setSession(s)
    }
  }, [session, settings])

  const resolveScriptText = useCallback(async (): Promise<string> => {
    const live = getLiveScript()
    if (live.trim()) return live
    if (!session) return ''
    const r = await api.exportRecordingScript(session.id)
    return r.content
  }, [session, getLiveScript])

  const exportScript = useCallback(async () => {
    return resolveScriptText()
  }, [resolveScriptText])

  const copyScript = useCallback(async () => {
    const text = await resolveScriptText()
    if (!text.trim()) throw new Error('No generated code yet — record an action first')
    await copyToClipboard(text)
  }, [resolveScriptText])

  const downloadScript = useCallback(async () => {
    const text = await resolveScriptText()
    if (!text.trim()) throw new Error('No generated code yet — record an action first')
    downloadTextFile(text, recordingFilename(settings.language_profile))
  }, [resolveScriptText, settings.language_profile])

  const state: RecordingState = session?.state ?? 'ready'
  const isRecording = state === 'recording'
  const isPaused = state === 'paused'
  const isActive = isRecording || isPaused

  return {
    session,
    settings,
    error,
    setError,
    elapsed,
    executing,
    state,
    isRecording,
    isPaused,
    isActive,
    getLiveScript,
    start,
    stop,
    pause,
    resume,
    clear,
    undo,
    redo,
    executeAction,
    deleteStep,
    reorderSteps,
    toggleStep,
    updateStepComment,
    updateSettings,
    exportScript,
    copyScript,
    downloadScript,
    refresh,
  }
}
