import { adminApi, formatInr } from './api'
import { useAdminPoll } from './useAdminPoll'

export default function AdminRevenue() {
  const { data, loading, error } = useAdminPoll(() => adminApi.revenue('30d'))

  if (loading && !data) return <div className="admin-loading">Loading revenue…</div>
  if (error && !data) return <div className="admin-error">{error}</div>
  if (!data) return null

  return (
    <div>
      <header className="admin-page-header">
        <div>
          <h1>Revenue</h1>
          <p className="admin-subtitle">All amounts in INR (₹)</p>
        </div>
        <span className="admin-refresh-hint">Auto-refreshes every 45s</span>
      </header>

      <div className="admin-kpi-grid">
        <div className="admin-kpi-card">
          <div className="label">Today</div>
          <div className="value">{formatInr(data.today_inr)}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">This Week</div>
          <div className="value">{formatInr(data.week_inr)}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">This Month</div>
          <div className="value">{formatInr(data.month_inr)}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">All Time</div>
          <div className="value">{formatInr(data.total_inr)}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">ARPU</div>
          <div className="value">{formatInr(Math.round(data.arpu_inr))}</div>
        </div>
      </div>

      <section className="admin-panel">
        <h2>Revenue Summary</h2>
        <p style={{ color: 'var(--admin-muted)', fontSize: '0.9rem' }}>
          Average revenue per user is {formatInr(Math.round(data.arpu_inr))} across all registered accounts.
          Period: {data.period}.
        </p>
      </section>
    </div>
  )
}
