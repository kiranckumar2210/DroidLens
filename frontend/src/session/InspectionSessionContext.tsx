import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api/client'
import { DEFAULT_BUILDER, type BuilderState, type InspectorSection } from '../components/InspectorPanel'
import { useLiveRefresh } from '../hooks/useLiveRefresh'
import type {
  ElementInspectionResult,
  InspectionSession,
  LocatorCandidate,
} from '../types'
import {
  defaultPersistedState,
  loadPersistedState,
  savePersistedState,
  snapshotFromSession,
  type AppScreen,
  type PersistedInspectionState,
  type SessionKind,
} from './storage'
import { loadXmlPackagePair } from '../offline/loadPackage'
import { addRecentFile } from '../offline/recentFiles'
import type { XmlPackagePair } from '../offline/xmlPackage'
import { liveSessionLog, restoreLiveSession } from './liveSessionManager'

export interface InspectionSessionContextValue {
  screen: AppScreen
  sessionKind: SessionKind
  deviceId: string
  session: InspectionSession | null
  inspection: ElementInspectionResult | null
  selectedLocator: LocatorCandidate | null
  liveRefresh: boolean
  refreshing: boolean
  connecting: boolean
  restoring: boolean
  restoreError: string | null
  packageName: string
  activity: string
  languageProfile: string
  codeAction: string
  inspectorSection: InspectorSection
  builderState: BuilderState
  highlightIds: string[]
  setPackageName: (v: string) => void
  setActivity: (v: string) => void
  setLanguageProfile: (v: string) => void
  setCodeAction: (v: string) => void
  setInspectorSection: (v: InspectorSection) => void
  setBuilderState: React.Dispatch<React.SetStateAction<BuilderState>>
  setHighlightIds: (ids: string[]) => void
  setLiveRefresh: (v: boolean) => void
  setSelectedLocator: (loc: LocatorCandidate | null) => void
  enterLiveInspector: (devId: string, pkg?: string) => Promise<void>
  enterOfflinePackages: (pairs: XmlPackagePair[], startIndex?: number) => Promise<void>
  enterOfflineInspector: (xml?: File, screenshot?: File) => Promise<void>
  switchOfflinePackage: (index: number) => Promise<void>
  offlinePackages: XmlPackagePair[]
  activePackageIndex: number
  currentPackageLabel: string
  enterMockInspector: () => Promise<void>
  backToDashboard: () => void
  retryRestore: () => Promise<void>
  refreshInspection: () => Promise<void>
  applySessionUpdate: (s: InspectionSession, opts?: { preserveSelection?: boolean }) => Promise<void>
  selectAt: (x: number, y: number) => Promise<void>
  selectById: (elementId: string) => Promise<void>
  selectLocator: (loc: LocatorCandidate) => Promise<void>
  selectedElementIdRef: React.MutableRefObject<string | null>
}

const InspectionSessionContext = createContext<InspectionSessionContextValue | null>(null)

export function useInspectionSession(): InspectionSessionContextValue {
  const ctx = useContext(InspectionSessionContext)
  if (!ctx) throw new Error('useInspectionSession must be used within InspectionSessionProvider')
  return ctx
}

interface ProviderProps {
  children: ReactNode
  onNotify: (message: string, kind?: 'info' | 'success' | 'warning' | 'error') => void
  onGeneratedCode?: (code: string, pageObject: string) => void
}

export function InspectionSessionProvider({
  children,
  onNotify,
  onGeneratedCode,
}: ProviderProps) {
  const initial = loadPersistedState()
  const restoringRef = useRef(false)

  const [screen, setScreen] = useState<AppScreen>(initial.screen)
  const [sessionKind, setSessionKind] = useState<SessionKind>(initial.sessionKind)
  const [deviceId, setDeviceId] = useState(initial.deviceId)
  const [session, setSession] = useState<InspectionSession | null>(null)
  const [inspection, setInspection] = useState<ElementInspectionResult | null>(null)
  const [selectedLocator, setSelectedLocator] = useState<LocatorCandidate | null>(null)
  const [liveRefresh, setLiveRefresh] = useState(initial.liveRefresh)
  const [refreshing, setRefreshing] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [restoring, setRestoring] = useState(
    () => initial.screen === 'inspector' && Boolean(initial.sessionDeviceId || initial.deviceId),
  )
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const [packageName, setPackageName] = useState(initial.packageName)
  const [activity, setActivity] = useState(initial.activity)
  const [languageProfile, setLanguageProfile] = useState(initial.languageProfile)
  const [codeAction, setCodeAction] = useState(initial.codeAction)
  const [inspectorSection, setInspectorSection] = useState<InspectorSection>(initial.inspectorSection)
  const [builderState, setBuilderState] = useState<BuilderState>(initial.builderState)
  const [highlightIds, setHighlightIds] = useState<string[]>([])
  const [offlinePackages, setOfflinePackages] = useState<XmlPackagePair[]>([])
  const [activePackageIndex, setActivePackageIndex] = useState(0)
  const selectedElementIdRef = useRef<string | null>(initial.selectedElementId)

  const persist = useCallback((patch: Partial<PersistedInspectionState>) => {
    savePersistedState({ ...loadPersistedState(), ...patch })
  }, [])

  const previewLocatorInternal = useCallback(async (loc: LocatorCandidate) => {
    if (!deviceId) return
    try {
      const r = await api.previewLocator(deviceId, loc.locator_type, loc.value)
      setHighlightIds(r.matched_ids || [])
    } catch { /* ignore */ }
  }, [deviceId])

  const generateCodeFor = useCallback(async (
    loc: LocatorCandidate,
    profile = languageProfile,
    action = codeAction,
  ) => {
    const name = (inspection?.element.text || inspection?.element.resource_id?.split('/').pop() || 'element')
      .toLowerCase().replace(/[^a-z0-9_]/g, '_')
    const script = await api.generateCode(
      loc, profile, action, name, packageName || 'com.example.app',
    )
    onGeneratedCode?.(script.code, script.page_object || '')
    return script
  }, [languageProfile, codeAction, inspection, packageName, onGeneratedCode])

  const applySessionUpdate = useCallback(async (
    s: InspectionSession,
    opts: { preserveSelection?: boolean } = { preserveSelection: true },
  ) => {
    setSession(s)
    setDeviceId(s.device_id)
    persist({
      deviceId: s.device_id,
      ...snapshotFromSession(s),
    })

    if (!opts.preserveSelection) return

    const eid = selectedElementIdRef.current
    if (!eid || !s.device_id) return

    try {
      const result = await api.selectById(s.device_id, eid)
      setInspection(result)
      setHighlightIds([result.element.id])
      selectedElementIdRef.current = result.element.stable_key || result.element.id
      const top = result.locators.find((l) => l.recommended) || result.locators[0]
      setSelectedLocator(top ?? null)
      if (top) await generateCodeFor(top)
    } catch {
      /* element may have moved off-screen — keep last inspection visible */
    }
  }, [generateCodeFor, persist])

  useLiveRefresh({
    deviceId: sessionKind === 'live' && session?.mode === 'live' ? deviceId : null,
    platform: 'android',
    enabled: liveRefresh && !!session && sessionKind === 'live' && screen === 'inspector',
    interval: 2,
    onSessionUpdate: (s) => { void applySessionUpdate(s) },
    onError: (msg) => onNotify(`Live: ${msg}`, 'warning'),
    onStatusChange: () => {},
  })

  useEffect(() => {
    if (restoringRef.current) return
    persist({
      screen,
      sessionKind,
      deviceId,
      liveRefresh,
      packageName,
      activity,
      languageProfile,
      codeAction,
      inspectorSection,
      builderState,
      selectedElementId: selectedElementIdRef.current,
      ...snapshotFromSession(session),
    })
  }, [
    screen, sessionKind, deviceId, liveRefresh, packageName, activity,
    languageProfile, codeAction, inspectorSection, builderState, session, persist,
  ])

  const runRestore = useCallback(async () => {
    const devId = loadPersistedState().sessionDeviceId || loadPersistedState().deviceId
    const kind = loadPersistedState().sessionKind
    const pkg = loadPersistedState().packageName
    const selectedId = loadPersistedState().selectedElementId

    if (!devId) {
      setRestoring(false)
      setRestoreError(null)
      return
    }

    setRestoring(true)
    setRestoreError(null)

    try {
      const s = await restoreLiveSession({
        deviceId: devId,
        sessionKind: kind,
        packageName: pkg || undefined,
      })
      setSession(s)
      setDeviceId(s.device_id)
      setSessionKind(kind)
      setScreen('inspector')
      if (kind === 'live') {
        setLiveRefresh(loadPersistedState().liveRefresh)
      }
      if (selectedId) {
        selectedElementIdRef.current = selectedId
        try {
          const result = await api.selectById(s.device_id, selectedId)
          setInspection(result)
          setHighlightIds([result.element.id])
          const top = result.locators.find((l) => l.recommended) || result.locators[0]
          setSelectedLocator(top ?? null)
        } catch { /* ignore */ }
      }
      onNotify('Inspection session restored', 'success')
    } catch (err) {
      const msg = (err as Error).message
      liveSessionLog('session_restore_failed', { deviceId: devId, error: msg })
      setRestoreError(msg)
      onNotify('Could not restore session — use Reconnect or return to Dashboard', 'warning')
    } finally {
      setRestoring(false)
    }
  }, [onNotify])

  useEffect(() => {
    if (initial.screen !== 'inspector' || restoringRef.current) return
    if (!initial.sessionDeviceId && !initial.deviceId) return
    restoringRef.current = true
    void runRestore().finally(() => {
      restoringRef.current = false
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const enterLiveInspector = useCallback(async (devId: string, pkg?: string) => {
    setSessionKind('live')
    setDeviceId(devId)
    if (pkg) setPackageName(pkg)
    setConnecting(true)
    setInspection(null)
    setSelectedLocator(null)
    setHighlightIds([])
    selectedElementIdRef.current = null
    try {
      const s = await api.connect(devId, 'android', pkg)
      if (s.mode !== 'live') throw new Error('Server returned non-live session')
      if (s.device_id.startsWith('mock-')) throw new Error('Received mock device session during live connect')
      setSession(s)
      setLiveRefresh(true)
      setScreen('inspector')
      persist({
        screen: 'inspector',
        sessionKind: 'live',
        deviceId: devId,
        liveRefresh: true,
        packageName: pkg || packageName,
        ...snapshotFromSession(s),
      })
      onNotify(`Connected to ${s.device_id} (${s.last_refresh_ms}ms)`, 'success')
    } catch (e) {
      onNotify(`Live connect failed: ${(e as Error).message}`, 'error')
      throw e
    } finally {
      setConnecting(false)
    }
  }, [onNotify, packageName, persist])

  const applyOfflinePair = useCallback(async (pair: XmlPackagePair) => {
    const s = await loadXmlPackagePair(pair)
    setSession(s)
    setDeviceId(s.device_id)
    setSessionKind('offline')
    setLiveRefresh(false)
    setInspection(null)
    setSelectedLocator(null)
    selectedElementIdRef.current = null
    setScreen('inspector')
    persist({
      screen: 'inspector',
      sessionKind: 'offline',
      deviceId: s.device_id,
      liveRefresh: false,
      ...snapshotFromSession(s),
    })
    addRecentFile({
      xmlName: pair.label + '.xml',
      xmlPath: pair.xmlPath,
      screenshotPath: pair.screenshotPath,
    })
    return s
  }, [persist])

  const enterOfflinePackages = useCallback(async (pairs: XmlPackagePair[], startIndex = 0) => {
    if (!pairs.length) throw new Error('No XML packages to open')
    setConnecting(true)
    setOfflinePackages(pairs)
    setActivePackageIndex(startIndex)
    try {
      await applyOfflinePair(pairs[startIndex]!)
      onNotify(`Opened: ${pairs[startIndex]!.label}`, 'success')
    } finally {
      setConnecting(false)
    }
  }, [applyOfflinePair, onNotify])

  const switchOfflinePackage = useCallback(async (index: number) => {
    if (index < 0 || index >= offlinePackages.length) return
    setConnecting(true)
    setActivePackageIndex(index)
    try {
      await applyOfflinePair(offlinePackages[index]!)
      onNotify(`Switched to: ${offlinePackages[index]!.label}`, 'info')
    } finally {
      setConnecting(false)
    }
  }, [offlinePackages, applyOfflinePair, onNotify])

  const enterOfflineInspector = useCallback(async (xml?: File, screenshot?: File) => {
    if (!xml && !screenshot) throw new Error('Select an XML and/or screenshot file')
    const label = xml?.name.replace(/\.(xml|uix)$/i, '') || screenshot?.name.replace(/\.\w+$/, '') || 'Offline'
    await enterOfflinePackages([{
      id: label,
      label,
      xml,
      screenshot,
    }], 0)
  }, [enterOfflinePackages])

  const enterMockInspector = useCallback(async () => {
    setConnecting(true)
    try {
      const s = await api.loadMockSession()
      setSession(s)
      setDeviceId(s.device_id)
      setSessionKind('mock')
      setLiveRefresh(false)
      setInspection(null)
      setSelectedLocator(null)
      selectedElementIdRef.current = null
      setScreen('inspector')
      persist({
        screen: 'inspector',
        sessionKind: 'mock',
        deviceId: s.device_id,
        liveRefresh: false,
        ...snapshotFromSession(s),
      })
      onNotify('Sample project loaded', 'success')
    } finally {
      setConnecting(false)
    }
  }, [onNotify, persist])

  const backToDashboard = useCallback(() => {
    setScreen('dashboard')
    setLiveRefresh(false)
    setOfflinePackages([])
    setActivePackageIndex(0)
    persist({ screen: 'dashboard', liveRefresh: false })
    onNotify('Ready')
  }, [onNotify, persist])

  const currentPackageLabel = offlinePackages[activePackageIndex]?.label ?? ''

  const refreshInspection = useCallback(async () => {
    if (!deviceId || !session || sessionKind !== 'live' || screen !== 'inspector') return
    setRefreshing(true)
    try {
      const s = await api.refreshSessionWithRetry(deviceId, 'android', packageName || undefined)
      await applySessionUpdate(s)
      onNotify(`Refreshed in ${s.last_refresh_ms}ms`, 'success')
    } catch (e) {
      onNotify(`Refresh failed: ${(e as Error).message}`, 'error')
    } finally {
      setRefreshing(false)
    }
  }, [deviceId, session, sessionKind, screen, packageName, applySessionUpdate, onNotify])

  const selectAt = useCallback(async (x: number, y: number) => {
    const sid = session?.device_id
    if (!sid) return
    try {
      const result = await api.selectAt(sid, x, y)
      setInspection(result)
      setHighlightIds([result.element.id])
      selectedElementIdRef.current = result.element.stable_key || result.element.id
      persist({ selectedElementId: selectedElementIdRef.current })
      const top = result.locators.find((l) => l.recommended) || result.locators[0]
      setSelectedLocator(top ?? null)
      if (top) await generateCodeFor(top)
      onNotify(`Selected: ${result.element.text || result.element.class_name.split('.').pop()}`)
    } catch (e) {
      onNotify(`Selection failed: ${(e as Error).message}`, 'error')
    }
  }, [session, generateCodeFor, onNotify, persist])

  const selectById = useCallback(async (elementId: string) => {
    const sid = session?.device_id
    if (!sid) return
    try {
      const result = await api.selectById(sid, elementId)
      setInspection(result)
      setHighlightIds([elementId])
      selectedElementIdRef.current = result.element.stable_key || elementId
      persist({ selectedElementId: selectedElementIdRef.current })
      const top = result.locators[0] ?? null
      setSelectedLocator(top)
      if (top) await generateCodeFor(top)
    } catch (e) {
      onNotify(`Selection failed: ${(e as Error).message}`, 'error')
    }
  }, [session, generateCodeFor, onNotify, persist])

  const selectLocator = useCallback(async (loc: LocatorCandidate) => {
    setSelectedLocator(loc)
    await generateCodeFor(loc)
    await previewLocatorInternal(loc)
  }, [generateCodeFor, previewLocatorInternal])

  const value = useMemo<InspectionSessionContextValue>(() => ({
    screen,
    sessionKind,
    deviceId,
    session,
    inspection,
    selectedLocator,
    liveRefresh,
    refreshing,
    connecting,
    restoring,
    restoreError,
    packageName,
    activity,
    languageProfile,
    codeAction,
    inspectorSection,
    builderState,
    highlightIds,
    setPackageName,
    setActivity,
    setLanguageProfile,
    setCodeAction,
    setInspectorSection,
    setBuilderState,
    setHighlightIds,
    setLiveRefresh,
    setSelectedLocator,
    enterLiveInspector,
    enterOfflinePackages,
    enterOfflineInspector,
    switchOfflinePackage,
    offlinePackages,
    activePackageIndex,
    currentPackageLabel,
    enterMockInspector,
    backToDashboard,
    retryRestore: runRestore,
    refreshInspection,
    applySessionUpdate,
    selectAt,
    selectById,
    selectLocator,
    selectedElementIdRef,
  }), [
    screen, sessionKind, deviceId, session, inspection, selectedLocator,
    liveRefresh, refreshing, connecting, restoring, restoreError, packageName, activity,
    languageProfile, codeAction, inspectorSection, builderState, highlightIds,
    enterLiveInspector, enterOfflinePackages, enterOfflineInspector, switchOfflinePackage,
    offlinePackages, activePackageIndex, currentPackageLabel, enterMockInspector,
    backToDashboard, refreshInspection, applySessionUpdate,
    selectAt, selectById, selectLocator,
  ])

  return (
    <InspectionSessionContext.Provider value={value}>
      {children}
    </InspectionSessionContext.Provider>
  )
}

export { defaultPersistedState }
