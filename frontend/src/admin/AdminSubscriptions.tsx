import { adminApi } from './api'
import { useAdminPoll } from './useAdminPoll'

export default function AdminSubscriptions() {
  const { data, loading, error } = useAdminPoll(() => adminApi.subscriptions())

  if (loading && !data) return <div className="admin-loading">Loading subscriptions…</div>
  if (error && !data) return <div className="admin-error">{error}</div>
  if (!data) return null

  return (
    <div>
      <header className="admin-page-header">
        <div>
          <h1>Subscriptions</h1>
          <p className="admin-subtitle">License and trial breakdown</p>
        </div>
        <span className="admin-refresh-hint">Auto-refreshes every 45s</span>
      </header>

      <div className="admin-kpi-grid">
        <div className="admin-kpi-card">
          <div className="label">Trial Active</div>
          <div className="value">{data.trial_active}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Trial Expired</div>
          <div className="value">{data.trial_expired}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Lifetime Users</div>
          <div className="value">{data.lifetime_users}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Conversion Rate</div>
          <div className="value">{data.conversion_rate}%</div>
        </div>
      </div>

      <section className="admin-panel">
        <h2>Subscription Funnel</h2>
        <p style={{ color: 'var(--admin-muted)', fontSize: '0.9rem' }}>
          {data.trial_active} users are currently on an active trial.
          {data.lifetime_users} have converted to lifetime licenses
          ({data.conversion_rate}% of all registered users).
        </p>
      </section>
    </div>
  )
}
