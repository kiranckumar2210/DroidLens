import { useCallback, useMemo, useState } from 'react'
import {
  BookOpen, Bug, ClipboardCopy, Cpu, ExternalLink, Info, Key,
  Mail, RefreshCw, ScrollText, X,
} from 'lucide-react'
import { getApiDocsUrl, isElectron } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { LicenseInfo } from '../auth/types'
import {
  ABOUT_DESCRIPTION, FEATURE_CATEGORIES, RELEASE_NOTES_V1, RELEASE_NOTES_V11, RELEASE_NOTES_V12, TECH_STACK,
} from '../data/aboutContent'
import {
  APP_AUTHOR, APP_COPYRIGHT, APP_EMAIL, APP_NAME, APP_TAGLINE,
  buildVersionClipboardText, getAppVersion, getRuntimeLabel,
} from '../utils/appInfo'
import BrandLogo from './BrandLogo'
import { useToast } from './ui/Toast'

interface Props {
  open: boolean
  onClose: () => void
  onOpenLicense?: () => void
}

function licenseDisplayLabel(license: LicenseInfo | null, isLoggedIn: boolean): string {
  if (!isLoggedIn || !license) return 'Guest User'
  switch (license.status) {
    case 'lifetime': return 'Lifetime Licensed User'
    case 'trial_active': return 'Trial User'
    case 'trial_expired': return 'Trial Expired'
    case 'payment_pending': return 'Payment Pending'
    case 'subscription_active': return 'Subscription Active'
    case 'subscription_expired': return 'Subscription Expired'
    default: return license.plan_name || 'Registered User'
  }
}

function userDisplayLabel(isLoggedIn: boolean, fullName?: string, email?: string): string {
  if (!isLoggedIn) return 'Guest User'
  return fullName || email || 'Registered User'
}

export default function AboutDialog({ open, onClose, onOpenLicense }: Props) {
  const { toast } = useToast()
  const { user, license, isLoggedIn } = useAuth()
  const [releaseOpen, setReleaseOpen] = useState(false)

  const version = getAppVersion()
  const userLabel = userDisplayLabel(isLoggedIn, user?.full_name, user?.email)
  const licenseLabel = licenseDisplayLabel(license, isLoggedIn)

  const versionText = useMemo(
    () => buildVersionClipboardText({ version, userLabel, licenseLabel, email: user?.email }),
    [version, userLabel, licenseLabel, user?.email],
  )

  const copyText = useCallback(async (text: string, msg: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast(msg, 'success')
    } catch {
      toast('Could not copy to clipboard', 'error')
    }
  }, [toast])

  const openDocs = () => {
    window.open(getApiDocsUrl(), '_blank', 'noopener,noreferrer')
  }

  const reportIssue = () => {
    const subject = encodeURIComponent(`${APP_NAME} Bug Report (v${version})`)
    const body = encodeURIComponent(
      `Please describe the issue:\n\n\n---\n${APP_NAME} ${version}\n${getRuntimeLabel()}\nUser: ${userLabel}\nLicense: ${licenseLabel}`,
    )
    window.open(`mailto:${APP_EMAIL}?subject=${subject}&body=${body}`, '_blank')
  }

  if (!open) return null

  return (
    <div className="auth-overlay about-overlay" role="dialog" aria-modal="true" aria-label="About DroidLens">
      <div className="about-dialog">
        <header className="about-header">
          <div className="about-header-brand">
            <BrandLogo size={56} />
            <div>
              <h2>{APP_NAME}</h2>
              <p className="about-tagline">{APP_TAGLINE}</p>
              <span className="about-version-badge">Version {version}</span>
              <span className="about-runtime-badge">{getRuntimeLabel()}</span>
            </div>
          </div>
          <button type="button" className="btn-icon copy-btn about-close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </header>

        <div className="about-scroll">
          <section className="about-section">
            <h3><Info size={16} /> Description</h3>
            {ABOUT_DESCRIPTION.split('\n\n').map((p) => (
              <p key={p.slice(0, 24)} className="about-desc">{p}</p>
            ))}
          </section>

          <section className="about-section">
            <h3><Cpu size={16} /> Key Features</h3>
            <div className="about-feature-grid">
              {FEATURE_CATEGORIES.map((cat) => {
                const Icon = cat.icon
                return (
                  <article key={cat.id} className="about-feature-card">
                    <div className="about-feature-card-head">
                      <Icon size={18} />
                      <h4>{cat.title}</h4>
                    </div>
                    <ul>
                      {cat.items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </article>
                )
              })}
            </div>
          </section>

          <section className="about-section">
            <h3>Technology Stack</h3>
            <div className="about-tech-list">
              {TECH_STACK.map((t) => (
                <span key={t} className="about-tech-chip">{t}</span>
              ))}
            </div>
          </section>

          <section className="about-section about-author-card">
            <h3>Author</h3>
            <p className="about-author-name">{APP_AUTHOR}</p>
            <button
              type="button"
              className="about-email-link"
              onClick={() => copyText(APP_EMAIL, 'Email copied')}
              title="Click to copy email"
            >
              <Mail size={14} />
              {APP_EMAIL}
            </button>
          </section>

          <section className="about-section about-license-card">
            <h3><Key size={16} /> License Information</h3>
            <div className="about-license-grid">
              <div className="about-license-row">
                <span>Current User</span>
                <strong>{userLabel}</strong>
              </div>
              {isLoggedIn && user?.email && (
                <div className="about-license-row">
                  <span>Email</span>
                  <span className="mono">{user.email}</span>
                </div>
              )}
              <div className="about-license-row">
                <span>Current License</span>
                <strong className={`license-status-${license?.status ?? 'guest'}`}>{licenseLabel}</strong>
              </div>
              {license?.days_remaining != null && license.status === 'trial_active' && (
                <div className="about-license-row">
                  <span>Trial Remaining</span>
                  <span>{license.days_remaining} day{license.days_remaining === 1 ? '' : 's'}</span>
                </div>
              )}
            </div>
          </section>

          {releaseOpen && (
            <section className="about-section about-release-panel">
              <h3><ScrollText size={16} /> Release Notes — v{version}</h3>
              <ul>
                {(version.startsWith('1.2') ? RELEASE_NOTES_V12 : version.startsWith('1.1') ? RELEASE_NOTES_V11 : RELEASE_NOTES_V1).map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </section>
          )}

          <section className="about-section">
            <h3>Useful Actions</h3>
            <div className="about-actions">
              <button type="button" className="about-action-btn" onClick={openDocs}>
                <BookOpen size={16} /> Documentation
                <ExternalLink size={12} className="about-action-ext" />
              </button>
              <button type="button" className="about-action-btn" onClick={() => setReleaseOpen((v) => !v)}>
                <ScrollText size={16} /> Release Notes
              </button>
              <button type="button" className="about-action-btn" onClick={reportIssue}>
                <Bug size={16} /> Report an Issue
              </button>
              <button
                type="button"
                className="about-action-btn disabled"
                disabled
                title="Coming Soon"
              >
                <RefreshCw size={16} /> Check for Updates
                <span className="about-soon">Soon</span>
              </button>
              <button
                type="button"
                className="about-action-btn"
                onClick={() => copyText(versionText, 'Version info copied')}
              >
                <ClipboardCopy size={16} /> Copy Version Info
              </button>
              {onOpenLicense && (
                <button
                  type="button"
                  className="about-action-btn"
                  onClick={() => { onClose(); onOpenLicense() }}
                >
                  <Key size={16} /> License Details
                </button>
              )}
            </div>
          </section>
        </div>

        <footer className="about-footer">
          <p className="about-footer-tagline"><strong>{APP_NAME}</strong> — {APP_TAGLINE}</p>
          <p>Built with ❤️ for the Mobile Automation Community.</p>
          <p className="about-copyright">{APP_COPYRIGHT}</p>
          {isElectron() && <p className="about-footer-meta">Desktop build · Electron</p>}
        </footer>
      </div>
    </div>
  )
}
