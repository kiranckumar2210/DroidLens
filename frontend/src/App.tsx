import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  CircleDot, Code2, Download, FileUp, Info, Play, Radio, RefreshCw, Save, Search, ShieldAlert,
} from 'lucide-react'
import { api } from './api/client'
import { useAuth } from './auth/AuthContext'
import { useSystemConfig } from './auth/SystemConfigContext'
import { licenseBadgeText } from './auth/features'
import { usePremiumGate } from './auth/usePremiumGate'
import AdminApp from './admin/AdminApp'
import AboutDialog from './components/AboutDialog'
import BrandLogo from './components/BrandLogo'
import CodeGeneratorModal from './components/CodeGeneratorModal'
import Dashboard, { DashboardBackButton } from './components/Dashboard'
import DevicePanel from './components/DevicePanel'
import ElementTree from './components/ElementTree'
import ImportXmlPackageDialog from './components/ImportXmlPackageDialog'
import InspectorPanel from './components/InspectorPanel'
import LocatorHealthDialog from './components/LocatorHealthDialog'
import LocatorExportModal from './components/LocatorExportModal'
import SaveModal from './components/SaveModal'
import OfflineScreenNav from './components/OfflineScreenNav'
import ScreenshotPanel from './components/ScreenshotPanel'
import StatusBar from './components/StatusBar'
import ThemeSwitcher from './components/ui/ThemeSwitcher'
import { SplitPane } from './components/ui/SplitPane'
import { useToast } from './components/ui/Toast'
import AccountPage from './components/auth/AccountPage'
import LoginModal from './components/auth/LoginModal'
import PremiumGateDialog from './components/auth/PremiumGateDialog'
import RegisterModal from './components/auth/RegisterModal'
import SubscriptionPage from './components/auth/SubscriptionPage'
import SessionRecoveryBanner from './components/SessionRecoveryBanner'
import DevModeBanner from './components/DevModeBanner'
import RecordingStudio from './components/recording/RecordingStudio'
import ErrorBoundary from './components/ui/ErrorBoundary'
import { useRecording } from './recording/useRecording'
import { liveSessionLog } from './session/liveSessionManager'
import { exportXmlPackage } from './offline/exportPackage'
import { loadPackageNote } from './offline/packageNotes'
import { resetApplicationState } from './session/resetState'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { loadNavState, saveAuthOverlay, saveNavState, type AuthOverlay, type CheckoutStep } from './auth/navigationStorage'
import { loadPersistedState, savePersistedState } from './session/storage'
import { withTimeout } from './utils/withTimeout'
import { useTheme } from './hooks/useTheme'
import {
  InspectionSessionProvider,
  useInspectionSession,
} from './session/InspectionSessionContext'
import type { AdbStatus, DeviceInfo } from './types'
import { countElements } from './utils/treeUtils'
import './styles/app.css'
import './styles/recording-studio.css'

export default function App() {
  const path = window.location.pathname
  if (path.startsWith('/admin')) {
    return <AdminApp />
  }

  const { toast } = useToast()
  const [generatedCode, setGeneratedCode] = useState('')
  const [pageObject, setPageObject] = useState('')

  const onNotify = useCallback((message: string, kind: 'info' | 'success' | 'warning' | 'error' = 'info') => {
    if (kind !== 'info') toast(message, kind)
  }, [toast])

  const onGeneratedCode = useCallback((code: string, po: string) => {
    setGeneratedCode(code)
    setPageObject(po)
  }, [])

  return (
    <InspectionSessionProvider onNotify={onNotify} onGeneratedCode={onGeneratedCode}>
      <ErrorBoundary
        label="DroidLens"
        fallback={(
          <div className="session-recovery-banner session-recovery-fullscreen">
            <div className="session-recovery-content">
              <strong>Something went wrong</strong>
              <p>The app encountered an error. Reset UI state to recover without losing your device connection.</p>
            </div>
            <div className="session-recovery-actions">
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={() => {
                  resetApplicationState()
                  window.location.reload()
                }}
              >
                Reset &amp; Reload
              </button>
            </div>
          </div>
        )}
      >
        <AppShell generatedCode={generatedCode} pageObject={pageObject} setGeneratedCode={setGeneratedCode} setPageObject={setPageObject} />
      </ErrorBoundary>
    </InspectionSessionProvider>
  )
}

function AuthBootScreen() {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const t = window.setTimeout(() => setSlow(true), 8000)
    return () => window.clearTimeout(t)
  }, [])
  return (
    <div className="auth-boot">
      <BrandLogo size={48} />
      <p className="auth-boot-text">Restoring your session…</p>
      {slow && (
        <button
          type="button"
          className="btn-secondary btn-sm auth-boot-skip"
          onClick={() => {
            resetApplicationState()
            window.location.reload()
          }}
        >
          Continue without restoring
        </button>
      )}
    </div>
  )
}

function AppShell({
  generatedCode,
  pageObject,
  setGeneratedCode,
  setPageObject,
}: {
  generatedCode: string
  pageObject: string
  setGeneratedCode: (v: string) => void
  setPageObject: (v: string) => void
}) {
  const { theme, setTheme, resolved } = useTheme()
  const { toast } = useToast()
  const sm = useInspectionSession()
  const auth = useAuth()
  const { config } = useSystemConfig()
  const { gateOpen, gateAccess, requestFeature, closeGate } = usePremiumGate()

  const [authOverlay, setAuthOverlayState] = useState<AuthOverlay>(() => loadNavState().authOverlay)
  const setAuthOverlay = useCallback((overlay: AuthOverlay) => {
    setAuthOverlayState(overlay)
    saveAuthOverlay(overlay)
  }, [])
  const [aboutOpen, setAboutOpen] = useState(false)
  const [paymentReturnId, setPaymentReturnId] = useState<string | null>(null)
  const [paymentReturnStep, setPaymentReturnStep] = useState<CheckoutStep | undefined>()
  const [devices, setDevices] = useState<DeviceInfo[]>([])
  const [codeModalOpen, setCodeModalOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchType, setSearchType] = useState('all')
  const [adb, setAdb] = useState<AdbStatus | null>(null)
  const [saveOpen, setSaveOpen] = useState(false)
  const [status, setStatus] = useState('Ready')
  const [wifiHost, setWifiHost] = useState('')
  const [zoom, setZoom] = useState(1)
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null)
  const [recorderOpen, setRecorderOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [locatorExportOpen, setLocatorExportOpen] = useState(false)
  const [healthOpen, setHealthOpen] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)

  const setRecordingModeOpen = useCallback((open: boolean) => {
    setRecorderOpen(open)
  }, [])

  const notify = useCallback((message: string, kind: 'info' | 'success' | 'warning' | 'error' = 'info') => {
    setStatus(message)
    if (kind !== 'info') toast(message, kind)
  }, [toast])

  const recording = useRecording(
    sm.sessionKind === 'live' ? sm.deviceId : null,
    sm.packageName,
  )

  const handleRecordingStart = useCallback(async () => {
    if (!sm.deviceId || !sm.session) return
    try {
      liveSessionLog('recording_initialized', { deviceId: sm.deviceId })
      await withTimeout(recording.start(), 30000, 'Start recording')
      const refreshed = await withTimeout(api.refreshSessionWithRetry(sm.deviceId, 'android', sm.packageName || undefined), 45000, 'Refresh hierarchy')
      await sm.applySessionUpdate(refreshed, { preserveSelection: true })
      liveSessionLog('live_session_preserved', { deviceId: sm.deviceId })
      notify('Recording started — inspector remains active', 'success')
    } catch (e) {
      liveSessionLog('recording_failed', { error: (e as Error).message })
      notify((e as Error).message, 'error')
    }
  }, [sm, recording, notify])

  const handleRecordingStop = useCallback(async () => {
    try {
      await recording.stop()
      liveSessionLog('recording_stopped', { deviceId: sm.deviceId })
      notify('Recording stopped', 'success')
    } catch (e) {
      notify((e as Error).message, 'error')
    }
  }, [recording, sm.deviceId, notify])

  const handleBackFromStudio = useCallback(async () => {
    if (recording.isActive) {
      const leave = window.confirm(
        'Leave Recording Studio? Active recording will be stopped. Your live device session will be preserved.',
      )
      if (!leave) return
      try {
        await recording.stop()
      } catch {
        /* continue exit */
      }
    }
    liveSessionLog('recording_cancelled', { deviceId: sm.deviceId })
    setRecordingModeOpen(false)
    notify('Returned to Live Inspector', 'info')
  }, [recording, sm.deviceId, notify, setRecordingModeOpen])

  useEffect(() => {
    api.health().then((h) => setAdb(h.adb)).catch(() => {})
    const persisted = loadPersistedState()
    if (persisted.recordingModeOpen) {
      savePersistedState({ ...persisted, recordingModeOpen: false })
    }
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('payment_return') === '1') {
      const paymentId = params.get('payment_id')
      if (paymentId) {
        setPaymentReturnId(paymentId)
        setPaymentReturnStep('status')
        setAuthOverlay('subscription')
        saveNavState({
          paymentId,
          checkoutStep: 'status',
          authOverlay: 'subscription',
        })
      }
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [setAuthOverlay])

  const loadDevices = useCallback(async (refresh = false) => {
    try {
      const { devices: list } = await api.listDevices(sm.platform, refresh)
      setDevices(list)
      setAdb(await api.adbStatus())
    } catch (e) {
      notify(`Error: ${(e as Error).message}`, 'error')
    }
  }, [notify])

  useEffect(() => {
    if (sm.screen === 'inspector' && sm.sessionKind === 'live') loadDevices()
  }, [sm.screen, sm.sessionKind, loadDevices])

  const elementName = () =>
    (sm.inspection?.element.text || sm.inspection?.element.resource_id?.split('/').pop() || 'element')
      .toLowerCase().replace(/[^a-z0-9_]/g, '_')

  const handleExportPackage = useCallback(async () => {
    let session = sm.session
    if (!session?.raw_xml || !session?.screenshot_base64) {
      notify('Nothing to export — refresh the session first', 'warning')
      return
    }
    try {
      if (sm.sessionKind === 'live' && sm.deviceId) {
        session = await api.refreshSessionWithRetry(sm.deviceId, 'android', sm.packageName || undefined)
        await sm.applySessionUpdate(session, { preserveSelection: true })
      }
      const baseName = sm.currentPackageLabel || sm.packageName?.split('.').pop() || 'CurrentScreen'
      const activePair = sm.offlinePackages[sm.activePackageIndex]
      const notes = activePair ? loadPackageNote(activePair) : undefined
      const xml = session.raw_xml!
      const screenshotBase64 = session.screenshot_base64!
      const out = await exportXmlPackage({
        xml,
        screenshotBase64,
        baseName,
        screenWidth: session.screen_width,
        screenHeight: session.screen_height,
        screenshotWidth: session.screenshot_width,
        screenshotHeight: session.screenshot_height,
        packageName: sm.packageName || session.package || undefined,
        deviceId: session.device_id,
        mode: sm.sessionKind,
        notes,
      })
      notify(`XML package exported: ${out}`, 'success')
    } catch (e) {
      notify((e as Error).message, 'error')
    }
  }, [sm, notify])

  useKeyboardShortcuts({
    enabled: sm.screen === 'inspector' && !recorderOpen,
    onRefresh: () => {
      if (sm.sessionKind === 'live' && sm.deviceId) void sm.refreshInspection()
    },
    onFocusSearch: () => searchInputRef.current?.focus(),
    onExport: () => requestFeature('session_save', () => setLocatorExportOpen(true)),
    onToggleLiveRefresh: () => {
      if (sm.sessionKind === 'live') sm.setLiveRefresh(!sm.liveRefresh)
    },
  })

  const handleOpenXmlPackages = useCallback(async (pairs: Parameters<typeof sm.enterOfflinePackages>[0], startIndex = 0) => {
    await sm.enterOfflinePackages(pairs, startIndex)
    notify(`Opened ${pairs.length} screen(s)`, 'success')
  }, [sm, notify])

  const handleInspectorDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    if (!files.length) return
    requestFeature('xml_upload', async () => {
      const { pairFilesFromList } = await import('./offline/xmlPackage')
      const pairs = pairFilesFromList(files)
      if (!pairs.length) {
        notify('Drop an XML file (.xml) with optional matching PNG', 'warning')
        return
      }
      try {
        await handleOpenXmlPackages(pairs, 0)
      } catch (err) {
        notify((err as Error).message, 'error')
      }
    })
  }, [handleOpenXmlPackages, notify, requestFeature])

  useEffect(() => {
    if (!sm.selectedLocator || !codeModalOpen) return
    void (async () => {
      const script = await api.generateCode(
        sm.selectedLocator!,
        sm.languageProfile,
        sm.codeAction,
        elementName(),
        sm.packageName || 'com.example.app',
      )
      setGeneratedCode(script.code)
      setPageObject(script.page_object || '')
    })()
  }, [sm.languageProfile, sm.codeAction, sm.selectedLocator, codeModalOpen, sm.packageName, sm.inspection, setGeneratedCode, setPageObject])

  const handleScreenshotClick = useCallback(async (x: number, y: number) => {
    await sm.selectAt(x, y)
  }, [sm])

  const sid = sm.session?.device_id || sm.deviceId
  const activeDevice = useMemo(
    () => devices.find((d) => d.id === sm.deviceId) || null,
    [devices, sm.deviceId],
  )
  const elementCount = useMemo(() => countElements(sm.session?.tree), [sm.session?.tree])
  const licenseLabel = licenseBadgeText(auth.license, auth.isLoggedIn)
  const hasPremium = auth.canAccess('code_generator').allowed

  const showSessionRecovery = sm.screen === 'inspector'
    && !sm.session
    && sm.sessionKind === 'live'
    && (sm.restoring || sm.restoreError || !sm.connecting)

  const handleReconnectDevice = useCallback(async () => {
    const devId = sm.deviceId || loadPersistedState().deviceId
    if (!devId) return
    try {
      await withTimeout(
        sm.enterLiveInspector(devId, sm.platform, sm.packageName || undefined),
        60000,
        'Reconnect',
      )
      notify('Reconnected to device', 'success')
    } catch (e) {
      notify((e as Error).message, 'error')
    }
  }, [sm, notify])

  const handleResetUi = useCallback(() => {
    setRecordingModeOpen(false)
    window.location.reload()
  }, [setRecordingModeOpen])

  const openLogin = () => setAuthOverlay('login')
  const openRegister = () => setAuthOverlay('register')
  const openAccount = () => setAuthOverlay('account')
  const openSubscription = () => {
    if (!config.subscription_enabled || !config.payment_enabled) return
    setAuthOverlay('subscription')
  }
  const openAbout = () => setAboutOpen(true)

  useEffect(() => {
    if (!auth.loading && authOverlay === 'account' && !auth.isLoggedIn) {
      setAuthOverlay('none')
    }
  }, [auth.loading, authOverlay, auth.isLoggedIn, setAuthOverlay])

  if (auth.loading) {
    return <AuthBootScreen />
  }

  if (authOverlay === 'account') {
    return (
      <AccountPage
        onBack={() => setAuthOverlay('none')}
        onOpenSubscription={openSubscription}
      />
    )
  }

  if (authOverlay === 'subscription') {
    if (!config.subscription_enabled || !config.payment_enabled) {
      return (
        <AccountPage
          onBack={() => setAuthOverlay('none')}
          onOpenSubscription={openSubscription}
        />
      )
    }
    return (
      <SubscriptionPage
        onBack={() => {
          setPaymentReturnId(null)
          setPaymentReturnStep(undefined)
          setAuthOverlay('none')
        }}
        initialPaymentId={paymentReturnId}
        initialStep={paymentReturnStep}
      />
    )
  }

  if (sm.screen === 'dashboard') {
    return (
      <>
        <DevModeBanner />
        <Dashboard
          theme={theme}
          onThemeChange={setTheme}
          onEnterLive={sm.enterLiveInspector}
          onOpenXmlPackages={sm.enterOfflinePackages}
          onEnterMock={sm.enterMockInspector}
          onNotify={notify}
          onOpenAccount={openAccount}
          onOpenSubscription={openSubscription}
          onOpenLogin={openLogin}
          onOpenRegister={openRegister}
          onOpenAbout={openAbout}
        />
        <AboutDialog
          open={aboutOpen}
          onClose={() => setAboutOpen(false)}
          onOpenLicense={openSubscription}
        />
        <LoginModal
          open={authOverlay === 'login'}
          onClose={() => setAuthOverlay('none')}
          onSwitchRegister={() => setAuthOverlay('register')}
        />
        <RegisterModal
          open={authOverlay === 'register'}
          onClose={() => setAuthOverlay('none')}
          onSwitchLogin={() => setAuthOverlay('login')}
        />
        <PremiumGateDialog
          open={gateOpen}
          access={gateAccess}
          onClose={closeGate}
          onSignIn={openLogin}
          onRegister={openRegister}
          onSubscribe={openSubscription}
        />
      </>
    )
  }

  return (
    <div
      className={`app ${dragOver ? 'app-drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleInspectorDrop}
    >
      <DevModeBanner />
      <header className="app-toolbar">
        <DashboardBackButton onClick={sm.backToDashboard} />
        <div className="toolbar-divider" />
        <div className="toolbar-brand">
          <BrandLogo size={26} />
          <div className="brand-text">
            <span className="brand-name">DroidLens</span>
            <span className="brand-tagline-inline">See. Inspect. Automate.</span>
          </div>
          <span className={`session-pill ${sm.sessionKind}`}>
            {sm.sessionKind === 'live' ? 'Live' : sm.sessionKind === 'offline' ? 'Offline' : 'Sample'}
          </span>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-actions">
          {sm.sessionKind === 'live' && (
            <>
              <input
                placeholder="Package"
                value={sm.packageName}
                onChange={(e) => sm.setPackageName(e.target.value)}
                className="pkg-input"
                aria-label="Package name"
              />
              <button
                type="button"
                className="btn-secondary"
                onClick={() => sm.packageName && api.launchApp(sm.deviceId, sm.packageName, sm.activity || undefined)}
                disabled={!sm.deviceId || !sm.packageName}
              >
                <Play size={14} /> Launch
              </button>
              <button
                type="button"
                className={`btn-secondary ${sm.refreshing ? 'loading' : ''}`}
                onClick={() => void sm.refreshInspection()}
                disabled={!sm.session || sm.refreshing || sm.connecting}
                aria-label="Refresh screenshot and hierarchy"
                title="Refresh screenshot and XML hierarchy"
              >
                <RefreshCw size={14} />
              </button>
              <button
                type="button"
                className={`btn-secondary ${recorderOpen || recording.isRecording ? 'rec-active' : ''}`}
                onClick={() => requestFeature('interaction_recorder', () => {
                  liveSessionLog('record_clicked', { deviceId: sm.deviceId })
                  setRecordingModeOpen(!recorderOpen)
                })}
                disabled={!sm.session}
                title="Toggle recording mode (stays in Live Inspector)"
              >
                <CircleDot size={14} /> Record
              </button>
              <button
                type="button"
                className={`btn-secondary live-toggle ${sm.liveRefresh ? 'active' : ''}`}
                onClick={() => sm.setLiveRefresh(!sm.liveRefresh)}
                disabled={!sm.session}
                title="Toggle automatic live refresh (every 2s)"
              >
                <Radio size={14} /> Auto
              </button>
            </>
          )}
          <button
            type="button"
            className="btn-primary"
            onClick={() => requestFeature('code_generator', () => setCodeModalOpen(true))}
            disabled={!sm.selectedLocator}
            title={hasPremium ? 'Generate automation code' : 'Requires account & license'}
          >
            <Code2 size={14} /> Code
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => requestFeature('xml_upload', () => setHealthOpen(true))}
            disabled={!sm.session?.raw_xml}
            title="Scan locator health for current XML"
          >
            <ShieldAlert size={14} /> Health
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void handleExportPackage()}
            disabled={!sm.session?.raw_xml || !sm.session?.screenshot_base64}
            title="Export XML + PNG to folder (UIAutomatorViewer style)"
          >
            <Download size={14} /> Export
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => requestFeature('xml_upload', () => setImportOpen(true))}
            title="Open XML + PNG package"
          >
            <FileUp size={14} /> Open
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => requestFeature('session_save', () => setSaveOpen(true))}
            disabled={!sm.inspection}
            aria-label="Save element"
            title={hasPremium ? 'Save to repository' : 'Requires account & license'}
          >
            <Save size={14} />
          </button>
          <ThemeSwitcher theme={theme} onChange={setTheme} />
          <button type="button" className="btn-icon copy-btn" onClick={openAbout} title="About DroidLens" aria-label="About DroidLens">
            <Info size={16} />
          </button>
        </div>

        <div className="toolbar-search">
          <Search size={14} aria-hidden />
          <select value={searchType} onChange={(e) => setSearchType(e.target.value)} aria-label="Search filter">
            <option value="all">All</option>
            <option value="text">Text</option>
            <option value="resource-id">ID</option>
            <option value="class">Class</option>
          </select>
          <input ref={searchInputRef} placeholder="Filter hierarchy… (Ctrl+F)" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} aria-label="Search hierarchy" />
        </div>
      </header>

      {recorderOpen && sm.sessionKind === 'live' && sm.session && (
        <ErrorBoundary
          label="Recording Studio"
          fallback={(
            <div className="recording-studio recording-mode-error">
              <span>Recording Studio failed to load.</span>
              <button type="button" className="btn-secondary btn-sm" onClick={() => setRecordingModeOpen(false)}>
                Back to Inspector
              </button>
            </div>
          )}
          onError={(err) => console.error('[Recording Studio]', err)}
        >
          <RecordingStudio
            recording={recording}
            theme={theme}
            resolvedTheme={resolved}
            session={sm.session}
            inspection={sm.inspection}
            selectedLocator={sm.selectedLocator}
            device={activeDevice}
            packageName={sm.packageName}
            activity={sm.activity}
            onSelectAt={handleScreenshotClick}
            onSelectById={(id) => sm.selectById(id)}
            onRefreshSession={sm.refreshInspection}
            onBack={() => void handleBackFromStudio()}
            onNotify={notify}
            onStart={() => void handleRecordingStart()}
            onStop={() => void handleRecordingStop()}
            onExecute={async (payload) => {
              try {
                await recording.executeAction(payload)
                if (sm.deviceId) {
                  try {
                    const refreshed = await api.refreshSessionWithRetry(
                      sm.deviceId,
                      'android',
                      sm.packageName || undefined,
                    )
                    await sm.applySessionUpdate(refreshed, { preserveSelection: true })
                  } catch (refreshErr) {
                    liveSessionLog('xml_refreshed', { deviceId: sm.deviceId, error: (refreshErr as Error).message })
                    notify('Action recorded — screenshot refresh failed, use Refresh in the screenshot panel', 'warning')
                  }
                }
                notify(`Recorded: ${payload.action_type.replace(/_/g, ' ')}`, 'success')
              } catch (e) {
                notify((e as Error).message, 'error')
              }
            }}
          />
        </ErrorBoundary>
      )}

      {!recorderOpen && showSessionRecovery && (
        <SessionRecoveryBanner
          restoring={sm.restoring}
          restoreError={sm.restoreError}
          deviceId={sm.deviceId}
          onRetry={() => void sm.retryRestore()}
          onReconnect={() => void handleReconnectDevice()}
          onDashboard={sm.backToDashboard}
          onReset={handleResetUi}
        />
      )}

      <div className={`inspector-layout ${showSessionRecovery && !recorderOpen ? 'workspace-blocked' : ''} ${recorderOpen ? 'workspace-behind-studio' : ''}`}>
        {sm.sessionKind === 'offline' && sm.offlinePackages.length > 1 && (
          <OfflineScreenNav
            packages={sm.offlinePackages}
            activeIndex={sm.activePackageIndex}
            onSelect={(idx) => void sm.switchOfflinePackage(idx)}
          />
        )}
      <div className={`workspace ${showSessionRecovery && !recorderOpen ? 'workspace-blocked' : ''} ${recorderOpen ? 'workspace-behind-studio' : ''}`}>
        <SplitPane side="left" initial={280} min={220} max={480} className="split-pane-left">
          <div className="split-pane-inner">
            <ElementTree
              tree={sm.session?.tree ?? null}
              selectedId={sm.inspection?.element.id}
              onSelect={(id) => void sm.selectById(id)}
              searchQuery={searchQuery}
              searchType={searchType}
            />
            {sm.sessionKind === 'live' ? (
              <DevicePanel
                embedded
                devices={devices}
                deviceId={sm.deviceId}
                adb={adb}
                mockMode={false}
                onSelect={(id) => {
                  if (id && id !== sm.deviceId) {
                    notify('Use Dashboard to switch to a different device', 'warning')
                  }
                }}
                onRefresh={() => loadDevices(true)}
                onRestartAdb={async () => { setAdb(await api.adbRestart()); loadDevices(true) }}
                wifiHost={wifiHost}
                onWifiHostChange={setWifiHost}
                onWifiConnect={async () => { await api.connectWifi(wifiHost); loadDevices(true) }}
              />
            ) : (
              <div className="panel device-panel-compact session-info-panel">
                <div className="panel-header">Session</div>
                <div className="device-panel-body">
                  <Detail label="Mode" value={sm.sessionKind} />
                  <Detail label="ID" value={sid} />
                  <Detail label="Platform" value="Android" />
                </div>
              </div>
            )}
          </div>
        </SplitPane>

        <section className="workspace-center">
          <ScreenshotPanel
            screenshot={sm.session?.screenshot_base64}
            screenshotWidth={
              sm.session?.coordinate_mapping?.screenshot_width
              || sm.session?.screenshot_width
              || sm.session?.screen_width
              || 1080
            }
            screenshotHeight={
              sm.session?.coordinate_mapping?.screenshot_height
              || sm.session?.screenshot_height
              || sm.session?.screen_height
              || 1920
            }
            hierarchyWidth={
              sm.session?.coordinate_mapping?.hierarchy_width
              || sm.session?.screen_width
              || 1080
            }
            hierarchyHeight={
              sm.session?.coordinate_mapping?.hierarchy_height
              || sm.session?.screen_height
              || 1920
            }
            tree={sm.session?.tree}
            selectedElement={sm.inspection?.element}
            highlightIds={sm.highlightIds}
            onClickCoords={(x, y) => void handleScreenshotClick(x, y)}
            onZoomChange={setZoom}
            onCursorMove={(x, y) => setCursor({ x, y })}
          />
        </section>

        <SplitPane side="right" initial={380} min={300} max={560} className="split-pane-right">
          <InspectorPanel
            inspection={sm.inspection}
            selectedLocator={sm.selectedLocator}
            onSelectLocator={(loc) => void sm.selectLocator(loc)}
            onPreviewLocator={async (loc) => {
              if (!sm.deviceId) return
              try {
                const r = await api.previewLocator(sm.deviceId, loc.locator_type, loc.value)
                sm.setHighlightIds(r.matched_ids || [])
              } catch { /* ignore */ }
            }}
            deviceId={sid || null}
            expandedSection={sm.inspectorSection}
            onSectionChange={(section) => {
              if (section === 'builder') {
                requestFeature('custom_locator_builder', () => sm.setInspectorSection(section))
                return
              }
              sm.setInspectorSection(section)
            }}
            builderState={sm.builderState}
            onBuilderStateChange={sm.setBuilderState}
            onHighlightMatches={sm.setHighlightIds}
            theme={resolved}
            premiumLocked={!hasPremium}
            elementName={elementName()}
            packageName={sm.packageName}
            screenName={sm.currentPackageLabel || sm.packageName || undefined}
            onExportLocators={() => requestFeature('session_save', () => setLocatorExportOpen(true))}
          />
        </SplitPane>
      </div>
      </div>

      {sm.refreshing && (
        <div className="refresh-overlay" aria-live="polite">
          <RefreshCw size={18} className="spin" />
          Refreshing…
        </div>
      )}

      <StatusBar
        adb={adb}
        device={activeDevice}
        session={sm.session}
        sessionKind={sm.sessionKind}
        theme={theme}
        zoom={zoom}
        coords={cursor}
        elementCount={elementCount}
        message={status}
        licenseLabel={licenseLabel}
        onLicenseClick={auth.user ? openAccount : openLogin}
      />

      <LoginModal
        open={authOverlay === 'login'}
        onClose={() => setAuthOverlay('none')}
        onSwitchRegister={() => setAuthOverlay('register')}
      />
      <RegisterModal
        open={authOverlay === 'register'}
        onClose={() => setAuthOverlay('none')}
        onSwitchLogin={() => setAuthOverlay('login')}
      />
      <PremiumGateDialog
        open={gateOpen}
        access={gateAccess}
        onClose={closeGate}
        onSignIn={openLogin}
        onRegister={openRegister}
        onSubscribe={openSubscription}
      />
      <AboutDialog
        open={aboutOpen}
        onClose={() => setAboutOpen(false)}
        onOpenLicense={openSubscription}
      />

      <CodeGeneratorModal
        open={codeModalOpen}
        onClose={() => setCodeModalOpen(false)}
        code={generatedCode}
        pageObject={pageObject}
        languageProfile={sm.languageProfile}
        action={sm.codeAction}
        onLanguageChange={sm.setLanguageProfile}
        onActionChange={sm.setCodeAction}
        elementName={elementName()}
      />

      <SaveModal
        open={saveOpen}
        onClose={() => setSaveOpen(false)}
        inspection={sm.inspection}
        primaryLocator={sm.selectedLocator}
        platform={sm.platform}
        onSave={async (data) => {
          if (!sm.inspection || !sm.selectedLocator) return
          await api.saveElement({
            ...data,
            platform: sm.platform,
            element: sm.inspection.element,
            primary_locator: sm.selectedLocator,
            all_locators: sm.inspection.locators,
            screenshot_base64: sm.session?.screenshot_base64,
            xml_content: sm.session?.raw_xml,
          })
          notify('Element saved to repository', 'success')
        }}
      />

      <ImportXmlPackageDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onOpen={handleOpenXmlPackages}
      />

      <LocatorExportModal
        open={locatorExportOpen}
        onClose={() => setLocatorExportOpen(false)}
        inspection={sm.inspection}
        screenName={sm.currentPackageLabel || sm.packageName || undefined}
        packageName={sm.packageName || sm.session?.package || undefined}
        elementName={elementName()}
        onNotify={notify}
      />

      <LocatorHealthDialog
        open={healthOpen}
        onClose={() => setHealthOpen(false)}
        initialXml={sm.session?.raw_xml}
        initialScreenName={sm.currentPackageLabel || sm.packageName || undefined}
        onNotify={notify}
      />
    </div>
  )
}

function Detail({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return (
    <div className="detail-row">
      <span>{label}</span>
      <span className="mono">{value}</span>
    </div>
  )
}
