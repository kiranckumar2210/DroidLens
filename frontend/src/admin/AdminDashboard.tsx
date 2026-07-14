import { adminApi, formatInr } from './api'
import { useAdminPoll } from './useAdminPoll'

function statusBadge(status: string) {
  const cls = status.includes('completed') || status === 'lifetime' || status === 'active' || status === 'success'
    ? 'success'
    : status.includes('fail') || status === 'suspended' || status === 'expired'
      ? 'danger'
      : status.includes('pending') || status === 'trial_active'
        ? 'warning'
        : 'neutral'
  return <span className={`admin-badge ${cls}`}>{status.replace(/_/g, ' ')}</span>
}

export default function AdminDashboard() {
  const { data, loading, error } = useAdminPoll(() => adminApi.dashboard())

  if (loading && !data) return <div className="admin-loading">Loading dashboard…</div>
  if (error && !data) return <div className="admin-error">{error}</div>
  if (!data) return null

  const maxDaily = Math.max(...data.registration.daily.map((d) => d.count), 1)

  return (
    <div>
      <header className="admin-page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="admin-subtitle">
            Real-time overview · Updated {new Date(data.updated_at).toLocaleTimeString()}
          </p>
        </div>
        <span className="admin-refresh-hint">Auto-refreshes every 45s</span>
      </header>

      <div className="admin-kpi-grid">
        <div className="admin-kpi-card">
          <div className="label">Total Users</div>
          <div className="value">{data.kpis.total_registered_users}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Active Trials</div>
          <div className="value">{data.kpis.active_trial_users}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Lifetime</div>
          <div className="value">{data.kpis.lifetime_subscribers}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Revenue</div>
          <div className="value">{formatInr(data.kpis.total_revenue_inr)}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Conversion</div>
          <div className="value">{data.kpis.trial_conversion_rate}%</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Active Sessions</div>
          <div className="value">{data.kpis.active_sessions}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Payments Today</div>
          <div className="value">{data.kpis.payments_today}</div>
        </div>
        <div className="admin-kpi-card">
          <div className="label">Guest Sessions</div>
          <div className="value">{data.kpis.guest_sessions_today}</div>
        </div>
      </div>

      <div className="admin-grid-2">
        <section className="admin-panel">
          <h2>Registrations ({data.registration.period})</h2>
          <div className="admin-kpi-grid" style={{ marginBottom: '1rem' }}>
            <div className="admin-kpi-card">
              <div className="label">Today</div>
              <div className="value">{data.registration.today}</div>
            </div>
            <div className="admin-kpi-card">
              <div className="label">This Week</div>
              <div className="value">{data.registration.this_week}</div>
            </div>
            <div className="admin-kpi-card">
              <div className="label">This Month</div>
              <div className="value">{data.registration.this_month}</div>
            </div>
          </div>
          <div className="admin-chart-bars">
            {data.registration.daily.map((d) => (
              <div
                key={d.date}
                className="admin-chart-bar"
                style={{ height: `${Math.max(8, (d.count / maxDaily) * 100)}%` }}
                title={`${d.date}: ${d.count}`}
              />
            ))}
          </div>
        </section>

        <section className="admin-panel">
          <h2>Recent Activity</h2>
          <ul className="admin-activity-list">
            {data.recent_activity.slice(0, 8).map((e) => (
              <li key={e.id} className="admin-activity-item">
                <time>{new Date(e.timestamp).toLocaleString()}</time>
                <span>
                  <strong>{e.action}</strong>
                  {e.user_email && ` · ${e.user_email}`}
                  {e.detail && <em> — {e.detail}</em>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="admin-grid-2">
        <section className="admin-panel">
          <h2>Recent Users</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>License</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td>{u.license_type}</td>
                    <td>{statusBadge(u.account_status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="admin-panel">
          <h2>Recent Payments</h2>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>User</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_payments.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{p.order_id}</td>
                    <td>{p.user_email}</td>
                    <td>{formatInr(p.amount_inr)}</td>
                    <td>{statusBadge(p.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
