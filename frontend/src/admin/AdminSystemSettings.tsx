import { useCallback, useEffect, useState } from 'react'
import { adminApi } from './api'
import type { FeatureFlags } from '../auth/types'

interface SettingsForm {
  subscription_enabled: boolean
  payment_enabled: boolean
  trial_enabled: boolean
  guest_access_enabled: boolean
  login_required_for_live: boolean
  trial_days: number
  lifetime_price_inr: number
  currency: string
  discount_percent: number
  promotional_message: string
  features: FeatureFlags
}

const FEATURE_LABELS: Record<keyof FeatureFlags, string> = {
  mock_inspector: 'Mock Inspector',
  live_inspector: 'Live Inspector',
  recorder: 'Interaction Recorder',
  xml_upload: 'XML Upload',
  screenshot_upload: 'Screenshot Upload',
  locator_builder: 'Locator Builder',
  code_generator: 'Code Generator',
  ai_features: 'AI Features',
  export: 'Export',
  device_manager: 'Device Manager',
  session_manager: 'Session Manager',
}

function Toggle({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
  hint?: string
}) {
  return (
    <label className="admin-settings-toggle">
      <span>
        <strong>{label}</strong>
        {hint && <small>{hint}</small>}
      </span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  )
}

export default function AdminSystemSettings() {
  const [form, setForm] = useState<SettingsForm | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getLicensingSettings()
      setForm({
        subscription_enabled: data.subscription.subscription_enabled,
        payment_enabled: data.payment.payment_enabled,
        trial_enabled: data.subscription.trial_enabled,
        guest_access_enabled: data.subscription.guest_access_enabled,
        login_required_for_live: data.subscription.login_required_for_live,
        trial_days: data.payment.trial_days,
        lifetime_price_inr: data.payment.lifetime_price_inr,
        currency: data.payment.currency,
        discount_percent: data.payment.discount_percent,
        promotional_message: data.payment.promotional_message,
        features: { ...data.features },
      })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const update = <K extends keyof SettingsForm>(key: K, value: SettingsForm[K]) => {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  const updateFeature = (key: keyof FeatureFlags, value: boolean) => {
    setForm((prev) => (
      prev ? { ...prev, features: { ...prev.features, [key]: value } } : prev
    ))
  }

  const save = async () => {
    if (!form) return
    try {
      setSaving(true)
      setError(null)
      await adminApi.updateLicensingSettings({
        ...form,
        ...form.features,
      })
      setMsg('Settings saved')
      setTimeout(() => setMsg(null), 3000)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (loading || !form) {
    return <div className="admin-loading">Loading system settings…</div>
  }

  return (
    <div>
      <header className="admin-page-header">
        <div>
          <h1>Licensing &amp; Subscription</h1>
          <p className="admin-subtitle">System Settings — control subscription, payments, and feature access</p>
        </div>
        <button type="button" className="admin-btn primary" disabled={saving} onClick={() => void save()}>
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </header>

      {msg && <div className="admin-success">{msg}</div>}
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-panel admin-settings-grid">
        <section>
          <h2>Subscription &amp; Access</h2>
          <Toggle
            label="Subscription System"
            hint="When off, all authenticated users get premium access"
            checked={form.subscription_enabled}
            onChange={(v) => update('subscription_enabled', v)}
          />
          <Toggle
            label="PhonePe / Payment"
            hint="Enable payment processing"
            checked={form.payment_enabled}
            onChange={(v) => update('payment_enabled', v)}
          />
          <Toggle
            label="Free Trial"
            checked={form.trial_enabled}
            onChange={(v) => update('trial_enabled', v)}
          />
          <Toggle
            label="Guest Access"
            checked={form.guest_access_enabled}
            onChange={(v) => update('guest_access_enabled', v)}
          />
          <Toggle
            label="Require Login for Live Devices"
            checked={form.login_required_for_live}
            onChange={(v) => update('login_required_for_live', v)}
          />
        </section>

        <section>
          <h2>Pricing</h2>
          <label className="admin-field">
            Trial Days
            <input
              className="admin-input"
              type="number"
              min={0}
              value={form.trial_days}
              onChange={(e) => update('trial_days', Number(e.target.value))}
            />
          </label>
          <label className="admin-field">
            Lifetime Price (INR)
            <input
              className="admin-input"
              type="number"
              min={0}
              value={form.lifetime_price_inr}
              onChange={(e) => update('lifetime_price_inr', Number(e.target.value))}
            />
          </label>
          <label className="admin-field">
            Currency
            <input
              className="admin-input"
              value={form.currency}
              onChange={(e) => update('currency', e.target.value)}
            />
          </label>
          <label className="admin-field">
            Discount %
            <input
              className="admin-input"
              type="number"
              min={0}
              max={100}
              value={form.discount_percent}
              onChange={(e) => update('discount_percent', Number(e.target.value))}
            />
          </label>
          <label className="admin-field">
            Promotional Message
            <input
              className="admin-input"
              value={form.promotional_message}
              onChange={(e) => update('promotional_message', e.target.value)}
            />
          </label>
        </section>

        <section className="admin-settings-features">
          <h2>Feature Flags</h2>
          {(Object.keys(FEATURE_LABELS) as Array<keyof FeatureFlags>).map((key) => (
            <Toggle
              key={key}
              label={FEATURE_LABELS[key]}
              checked={form.features[key]}
              onChange={(v) => updateFeature(key, v)}
            />
          ))}
        </section>
      </div>
    </div>
  )
}
