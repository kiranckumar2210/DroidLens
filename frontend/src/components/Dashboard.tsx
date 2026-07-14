import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Clock, Database, Info, Lock, Monitor, RefreshCw, Settings, Upload, User,
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useSystemConfig } from '../auth/SystemConfigContext'
import { dashboardStatusText, trialBannerText } from '../auth/features'
import { usePremiumGate } from '../auth/usePremiumGate'
import type { AdbStatus, DeviceInfo } from '../types'
import BrandLogo from './BrandLogo'
import PremiumGateDialog from './auth/PremiumGateDialog'
import ThemeSwitcher from './ui/ThemeSwitcher'
import type { ThemeMode } from '../hooks/useTheme'

export type InspectionEntry = 'live' | 'offline' | 'mock'

interface RecentSession {
  id: string
  label: string
  kind: InspectionEntry
  at: string
}

interface Props {
  theme: ThemeMode
  onThemeChange?: (theme: ThemeMode) => void
  onEnterLive: (deviceId: string, packageName?: string) => Promise<void>
  onEnterOffline: (xml?: File, screenshot?: File) => Promise<void>
  onEnterMock: () => Promise<void>
  onOpenAccount?: () => void
  onOpenSubscription?: () => void
  onOpenLogin?: () => void
  onOpenRegister?: () => void
  onOpenAbout?: () => void
}

const RECENT_KEY = 'droidlens-recent-sessions'

function loadRecent(): RecentSession[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
  } catch {
    return []
  }
}

export default function Dashboard({
  theme, onThemeChange, onEnterLive, onEnterOffline, onEnterMock,
  onOpenAccount, onOpenSubscription, onOpenLogin, onOpenRegister, onOpenAbout,
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
  const [recent, setRecent] = useState<RecentSession[]>(loadRecent)
  const fileRef = useRef<HTMLInputElement>(null)

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

  const pushRecent = (kind: InspectionEntry, label: string) => {
    const entry: RecentSession = { id: `${kind}-${Date.now()}`, kind, label, at: new Date().toISOString() }
    const next = [entry, ...loadRecent().filter((r) => r.label !== label)].slice(0, 5)
    localStorage.setItem(RECENT_KEY, JSON.stringify(next))
    setRecent(next)
  }

  const handleLive = () => {
    if (!deviceId) { setError('Select a connected device'); return }
    requestFeature('live_inspection', async () => {
      setLoading('live')
      setError(null)
      try {
        await onEnterLive(deviceId, packageName || undefined)
        pushRecent('live', deviceId)
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
      pushRecent('mock', 'Sample Project')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(null)
    }
  }

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    let xml: File | undefined
    let screenshot: File | undefined
    for (const f of Array.from(files)) {
      if (f.name.endsWith('.xml') || f.name.endsWith('.uix') || f.type.includes('xml')) xml = f
      else if (f.type.startsWith('image/')) screenshot = f
    }
    if (!xml && !screenshot) {
      setError('Select an XML dump and/or screenshot')
      return
    }
    requestFeature('xml_upload', async () => {
      setLoading('offline')
      setError(null)
      try {
        await onEnterOffline(xml, screenshot)
        pushRecent('offline', xml?.name || screenshot?.name || 'Offline dump')
      } catch (err) {
        setError((err as Error).message)
      } finally {
        setLoading(null)
        e.target.value = ''
      }
    })
  }

  const toggle = (id: typeof expanded) => setExpanded(expanded === id ? null : id)

  useEffect(() => {
    if (!expanded) return
    const t = window.setTimeout(() => {
      document.querySelector('.dl-card.expanded')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 80)
    return () => window.clearTimeout(t)
  }, [expanded])

  return (
    <div className="dashboard">
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
              {subscriptionOn && license?.status === 'lifetime' && <span className="license-pill lifetime">Lifetime License</span>}
              {subscriptionOn && license?.status === 'payment_pending' && <span className="license-pill pending">Payment Pending</span>}
              {subscriptionOn && trialText && <span className="license-pill trial">{trialText}</span>}
              {subscriptionOn && license?.status === 'trial_expired' && <span className="license-pill expired">Trial Expired</span>}
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
              <button type="button" className="btn-primary btn-sm" onClick={onOpenRegister}>
                {subscriptionOn ? 'Free Trial' : 'Sign Up'}
              </button>
            </>
          )}
          {onThemeChange && <ThemeSwitcher theme={theme} onChange={onThemeChange} />}
          <button type="button" className="btn-icon copy-btn" onClick={onOpenAbout} title="About DroidLens" aria-label="About DroidLens">
            <Info size={16} />
          </button>
        </div>
      </header>

      <main className="dashboard-scroll" tabIndex={0} aria-label="Dashboard">
        {statusBanner && (
          <div
            className={`dashboard-status-banner ${
              !subscriptionOn ? 'lifetime'
              : license?.status === 'lifetime' ? 'lifetime'
              : license?.status === 'payment_pending' ? 'pending'
              : license?.status === 'trial_active' ? 'trial'
              : license?.status === 'trial_expired' ? 'expired'
              : 'guest'
            }`}
            role="status"
          >
            {statusBanner}
          </div>
        )}

        <section className="dashboard-hero">
          <BrandLogo size={64} />
          <h1>DroidLens</h1>
          <p className="brand-tagline">See. Inspect. Automate.</p>
          <p>Enterprise-grade Android UI inspection for automation engineers.</p>
        </section>

        {error && <div className="dashboard-error" role="alert">{error}</div>}

        <div className="dashboard-grid">
          <article
            className={`dl-card ${expanded === 'live' ? 'expanded' : ''} ${liveLocked ? 'locked' : ''}`}
            onClick={() => toggle('live')}
          >
            {liveLocked && <Lock size={14} className="dl-card-lock" title="Requires account & active license" />}
            <div className="dl-card-icon live"><Monitor size={24} /></div>
            <h2>Connect Live Device</h2>
            <p>Inspect a connected Android phone or emulator via ADB with live screenshot and hierarchy refresh.</p>
            {expanded === 'live' && (
              <div className="dl-card-body" onClick={(e) => e.stopPropagation()}>
                {liveLocked && (
                  <p className="locked-hint">
                    {subscriptionOn
                      ? 'Sign in and start your free trial to connect live devices.'
                      : 'Sign in to connect live devices.'}
                  </p>
                )}
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
                  {loading === 'live' ? 'Connecting…' : liveLocked ? 'Sign In to Connect' : 'Start Live Inspection'}
                </button>
              </div>
            )}
          </article>

          <article className={`dl-card ${expanded === 'offline' ? 'expanded' : ''} ${offlineLocked ? 'locked' : ''}`} onClick={() => toggle('offline')}>
            {offlineLocked && <Lock size={14} className="dl-card-lock" title="Requires account & active license" />}
            <div className="dl-card-icon offline"><Upload size={24} /></div>
            <h2>Open XML Dump</h2>
            <p>Load a previously exported UI hierarchy XML with optional screenshot for offline analysis.</p>
            {expanded === 'offline' && (
              <div className="dl-card-body" onClick={(e) => e.stopPropagation()}>
                <input ref={fileRef} type="file" accept=".xml,.uix,image/*" multiple hidden onChange={handleFiles} />
                <button type="button" className="btn-primary card-action" onClick={() => fileRef.current?.click()} disabled={loading === 'offline'}>
                  {loading === 'offline' ? 'Loading…' : offlineLocked ? 'Sign In to Upload' : 'Choose Files & Inspect'}
                </button>
              </div>
            )}
          </article>

          <article className={`dl-card ${expanded === 'mock' ? 'expanded' : ''}`} onClick={() => toggle('mock')}>
            <div className="dl-card-icon mock"><Database size={24} /></div>
            <h2>Open Sample Project</h2>
            <p>Explore DroidLens with bundled sample XML and screenshot — no account required.</p>
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
            <h2>Recent Sessions</h2>
            <p>Quick access to your last inspection sessions.</p>
            {expanded === 'recent' && (
              <div className="dl-card-body" onClick={(e) => e.stopPropagation()}>
                {recent.length === 0 ? (
                  <p className="upload-hint">No recent sessions yet.</p>
                ) : (
                  <ul className="upload-list">
                    {recent.map((r) => (
                      <li key={r.id}>
                        <strong className="capitalize">{r.kind}</strong> — {r.label}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </article>
        </div>

        <footer className="dashboard-footer">
          {!isLoggedIn
            ? subscriptionOn
              ? 'Try the free sample project instantly. Create an account for a 7-day full-feature trial.'
              : 'Try the free sample project instantly. Sign in for full premium access.'
            : 'Select an inspection mode to begin.'}
        </footer>
      </main>

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
