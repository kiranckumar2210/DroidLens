import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Clock, Database, Download, FileUp, Info, Lock, Monitor, RefreshCw, Settings, User,
} from 'lucide-react'
import { api } from '../api/client'
import { isElectron } from '../api/baseUrl'
import { useAuth } from '../auth/AuthContext'
import { useSystemConfig } from '../auth/SystemConfigContext'
import { dashboardStatusText, trialBannerText } from '../auth/features'
import { usePremiumGate } from '../auth/usePremiumGate'
import { loadRecentFiles, type RecentFileEntry } from '../offline/recentFiles'
import type { XmlPackagePair } from '../offline/xmlPackage'
import type { AdbStatus, DeviceInfo } from '../types'
import BrandLogo from './BrandLogo'
import ImportXmlPackageDialog from './ImportXmlPackageDialog'
import PremiumGateDialog from './auth/PremiumGateDialog'
import ThemeSwitcher from './ui/ThemeSwitcher'
import type { ThemeMode } from '../hooks/useTheme'

export type InspectionEntry = 'live' | 'offline' | 'mock'

interface Props {
  theme: ThemeMode
  onThemeChange?: (theme: ThemeMode) => void
  onEnterLive: (deviceId: string, packageName?: string) => Promise<void>
  onOpenXmlPackages: (pairs: XmlPackagePair[], startIndex?: number) => Promise<void>
  onEnterMock: () => Promise<void>
  onNotify?: (message: string, kind?: 'info' | 'success' | 'warning' | 'error') => void
  onOpenAccount?: () => void
  onOpenSubscription?: () => void
  onOpenLogin?: () => void
  onOpenRegister?: () => void
  onOpenAbout?: () => void
}

export default function Dashboard({
  theme, onThemeChange, onEnterLive, onOpenXmlPackages, onEnterMock,
  onNotify, onOpenAccount, onOpenSubscription, onOpenLogin, onOpenRegister, onOpenAbout,
}: Props) {
  const { isLoggedIn, license, user, isAdmin, canAccess } = useAuth()
  const { config } = useSystemConfig()
  const subscriptionOn = config.subscription_enabled
  const { gateOpen, gateAccess, requestFeature, closeGate } = usePremiumGate()
  const [adb, setAdb] = useState<AdbStatus | null>(null)
  const [devices, setDevices] = useState<DeviceInfo[]>([])
  const [deviceId, setDeviceId] = useState('')
  const [packageName, setPackageName] = useState('')
  const [loading, setLoading] = useState<InspectionEntry | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<InspectionEntry | 'recent' | null>(null)
  const [recentFiles, setRecentFiles] = useState<RecentFileEntry[]>(loadRecentFiles)
  const [importOpen, setImportOpen] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const liveLocked = !canAccess('live_inspection').allowed
  const offlineLocked = !canAccess('xml_upload').allowed
  const trialText = trialBannerText(license, subscriptionOn)
  const statusBanner = dashboardStatusText(license, isLoggedIn, subscriptionOn)

  const refreshDevices = useCallback(async () => {
    try {
      const [{ devices: list }, status] = await Promise.all([
        api.listDevices(true),
        api.adbStatus(),
      ])
      setDevices(list)
      setAdb(status)
      if (list.length && !deviceId) setDeviceId(list[0].id)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [deviceId])

  useEffect(() => { refreshDevices() }, [refreshDevices])

  const openImport = () => {
    requestFeature('xml_upload', () => setImportOpen(true))
  }

  const handleLive = () => {
    if (!deviceId) { setError('Select a connected device'); return }
    requestFeature('live_inspection', async () => {
      setLoading('live')
      setError(null)
      try {
        await onEnterLive(deviceId, packageName || undefined)
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setLoading(null)
      }
    })
  }

  const handleMock = async () => {
    setLoading('mock')
    setError(null)
    try {
      await onEnterMock()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(null)
    }
  }

  const handleOpenPackages = async (pairs: XmlPackagePair[], startIndex = 0) => {
    setLoading('offline')
    setError(null)
    try {
      await onOpenXmlPackages(pairs, startIndex)
      setRecentFiles(loadRecentFiles())
    } catch (e) {
      setError((e as Error).message)
      throw e
    } finally {
      setLoading(null)
    }
  }

  const openRecentFile = (entry: RecentFileEntry) => {
    if (!entry.xmlPath || !isElectron()) {
      onNotify?.('Re-open this file with Open XML Package', 'info')
      openImport()
      return
    }
    requestFeature('xml_upload', async () => {
      setLoading('offline')
      try {
        await handleOpenPackages([{
          id: entry.xmlName,
          label: entry.xmlName.replace(/\.(xml|uix)$/i, ''),
          xmlPath: entry.xmlPath,
          screenshotPath: entry.screenshotPath,
        }])
      } catch { /* error set in handleOpenPackages */ }
    })
  }

  const handleDashboardDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    if (!files.length) return
    requestFeature('xml_upload', async () => {
      const { pairFilesFromList } = await import('../offline/xmlPackage')
      const pairs = pairFilesFromList(files)
      if (!pairs.length) {
        setError('Drop an XML file (.xml) with optional matching PNG')
        return
      }
      await handleOpenPackages(pairs, 0)
    })
  }

  const toggle = (id: typeof expanded) => setExpanded(expanded === id ? null : id)

  return (
    <div
      className={`dashboard ${dragOver ? 'dashboard-drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDashboardDrop}
    >
      <header className="dashboard-topbar">
        <div className="toolbar-brand">
          <BrandLogo size={32} />
          <div className="brand-text">
            <span className="brand-name">DroidLens</span>
            <span className="brand-tagline-inline">See. Inspect. Automate.</span>
          </div>
        </div>
        <div className="dashboard-auth-actions">
          {isLoggedIn ? (
            <>
              {!subscriptionOn && <span className="license-pill lifetime">Premium</span>}
              <button type="button" className="btn-secondary btn-sm" onClick={onOpenAccount}>
                <User size={14} /> {user?.full_name.split(' ')[0]}
              </button>
              {isAdmin && (
                <a href="/admin" className="btn-secondary btn-sm admin-nav-btn">
                  <Settings size={14} /> Admin
                </a>
              )}
            </>
          ) : (
            <>
              <button type="button" className="btn-secondary btn-sm" onClick={onOpenLogin}>Sign In</button>
              <button type="button" className="btn-primary btn-sm" onClick={onOpenRegister}>Sign Up</button>
            </>
          )}
          {onThemeChange && <ThemeSwitcher theme={theme} onChange={onThemeChange} />}
          <button type="button" className="btn-icon copy-btn" onClick={onOpenAbout} title="About DroidLens">
            <Info size={16} />
          </button>
        </div>
      </header>

      <main className="dashboard-scroll" tabIndex={0} aria-label="Dashboard">
        {statusBanner && (
          <div className="dashboard-status-banner lifetime" role="status">{statusBanner}</div>
        )}

        <section className="dashboard-hero">
          <BrandLogo size={64} />
          <h1>DroidLens</h1>
          <p className="brand-tagline">See. Inspect. Automate.</p>
          <p>Modern UIAutomatorViewer-style Android UI inspection — live ADB or offline XML + PNG.</p>
        </section>

        {error && <div className="dashboard-error" role="alert">{error}</div>}

        <div className="dashboard-grid">
          <article className={`dl-card ${expanded === 'live' ? 'expanded' : ''} ${liveLocked ? 'locked' : ''}`} onClick={() => toggle('live')}>
            {liveLocked && <Lock size={14} className="dl-card-lock" aria-hidden />}
            <div className="dl-card-icon live"><Monitor size={24} /></div>
            <h2>Connect Live Device</h2>
            <p>Capture XML + screenshot from a connected Android device via ADB.</p>
            {expanded === 'live' && (
              <div className="dl-card-body" onClick={(e) => e.stopPropagation()}>
                {adb && (
                  <div className="adb-summary">
                    <span className={adb.installed ? 'ok' : 'err'}>ADB {adb.installed ? 'ready' : 'not found'}</span>
                    <span>{adb.device_count} device(s)</span>
                    <button type="button" className="btn-icon copy-btn" onClick={refreshDevices} aria-label="Refresh devices">
                      <RefreshCw size={14} />
                    </button>
                  </div>
                )}
                <label className="field-label">Device</label>
                <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} className="full-width" disabled={liveLocked}>
                  {devices.length === 0 && <option value="">No devices detected</option>}
                  {devices.map((d) => (
                    <option key={d.id} value={d.id}>{d.name} — {d.model || d.id}</option>
                  ))}
                </select>
                <label className="field-label">Package (optional)</label>
                <input className="full-width" placeholder="com.example.app" value={packageName} onChange={(e) => setPackageName(e.target.value)} disabled={liveLocked} />
                <button type="button" className="btn-primary card-action" onClick={handleLive} disabled={loading === 'live' || !deviceId}>
                  {loading === 'live' ? 'Connecting…' : 'Start Live Inspection'}
                </button>
              </div>
            )}
          </article>

          <article className={`dl-card ${expanded === 'offline' ? 'expanded' : ''} ${offlineLocked ? 'locked' : ''}`} onClick={() => toggle('offline')}>
            {offlineLocked && <Lock size={14} className="dl-card-lock" aria-hidden />}
            <div className="dl-card-icon offline"><FileUp size={24} /></div>
            <h2>Open XML Package</h2>
            <p>Load UIAutomator XML dump + matching PNG screenshot. Auto-pairs <code>Login.xml</code> + <code>Login.png</code>.</p>
            {expanded === 'offline' && (
              <div className="dl-card-body" onClick={(e) => e.stopPropagation()}>
                <p className="upload-hint">Drag files onto the dashboard or use the import dialog.</p>
                <button type="button" className="btn-primary card-action" onClick={openImport} disabled={loading === 'offline'}>
                  {loading === 'offline' ? 'Loading…' : 'Open XML Package…'}
                </button>
              </div>
            )}
          </article>

          <article className={`dl-card ${expanded === 'mock' ? 'expanded' : ''}`} onClick={() => toggle('mock')}>
            <div className="dl-card-icon mock"><Database size={24} /></div>
            <h2>Open Sample Project</h2>
            <p>Explore DroidLens with bundled sample data — no device required.</p>
            {expanded === 'mock' && (
              <div className="dl-card-body" onClick={(e) => e.stopPropagation()}>
                <button type="button" className="btn-primary card-action" onClick={handleMock} disabled={loading === 'mock'}>
                  {loading === 'mock' ? 'Loading…' : 'Load Sample Data'}
                </button>
              </div>
            )}
          </article>

          <article className={`dl-card ${expanded === 'recent' ? 'expanded' : ''}`} onClick={() => toggle('recent')}>
            <div className="dl-card-icon recent"><Clock size={24} /></div>
            <h2>Recent Files</h2>
            <p>Quick access to recently opened XML files (paths only — no copies).</p>
            {expanded === 'recent' && (
              <div className="dl-card-body" onClick={(e) => e.stopPropagation()}>
                {recentFiles.length === 0 ? (
                  <p className="upload-hint">No recent files yet.</p>
                ) : (
                  <ul className="recent-files-list">
                    {recentFiles.map((r) => (
                      <li key={`${r.xmlPath ?? r.xmlName}-${r.openedAt}`}>
                        <button type="button" className="recent-file-btn" onClick={() => openRecentFile(r)}>
                          <Download size={12} aria-hidden />
                          {r.xmlName}
                        </button>
                        <span className="recent-file-time">{new Date(r.openedAt).toLocaleString()}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </article>
        </div>

        <footer className="dashboard-footer">
          Drop <strong>.xml</strong> + <strong>.png</strong> anywhere on this screen, or export packages from Live Inspector.
        </footer>
      </main>

      <ImportXmlPackageDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onOpen={handleOpenPackages}
      />

      <PremiumGateDialog
        open={gateOpen}
        access={gateAccess}
        onClose={closeGate}
        onSignIn={() => { closeGate(); onOpenLogin?.() }}
        onRegister={() => { closeGate(); onOpenRegister?.() }}
        onSubscribe={() => { closeGate(); onOpenSubscription?.() }}
      />
    </div>
  )
}

export function DashboardBackButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="back-btn" onClick={onClick} title="Back to Dashboard">
      ← Dashboard
    </button>
  )
}
