import { useCallback, useEffect, useState } from 'react'
import { adminApi } from './api'
import type { AdminUserRow } from './api'
import type { LicenseOverrideType } from '../auth/types'

function statusBadge(status: string) {
  const cls = status === 'active' || status === 'lifetime' ? 'success'
    : status === 'suspended' ? 'danger'
      : status.includes('trial') ? 'warning' : 'neutral'
  return <span className={`admin-badge ${cls}`}>{status.replace(/_/g, ' ')}</span>
}

export default function AdminUsers() {
  const [items, setItems] = useState<AdminUserRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [licenseFilter, setLicenseFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pageSize = 15

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await adminApi.listUsers({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
        license: licenseFilter || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter, licenseFilter])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => { void load() }, 45_000)
    return () => window.clearInterval(id)
  }, [load])

  const handleAction = async (action: string, userId: string, licenseType?: LicenseOverrideType) => {
    if (action === 'delete' && !window.confirm('Delete this user permanently?')) return
    try {
      if (action === 'suspend') await adminApi.suspendUser(userId)
      else if (action === 'reset') await adminApi.resetTrial(userId)
      else if (action === 'activate') await adminApi.activateLicense(userId)
      else if (action === 'set-license' && licenseType) await adminApi.setLicense(userId, licenseType)
      else if (action === 'delete') await adminApi.deleteUser(userId)
      await load()
    } catch (e) {
      alert((e as Error).message)
    }
  }

  const exportCsv = async () => {
    try {
      const csv = await adminApi.exportUsers({
        search: search || undefined,
        status: statusFilter || undefined,
        license: licenseFilter || undefined,
      })
      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'users.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div>
      <header className="admin-page-header">
        <div>
          <h1>Users</h1>
          <p className="admin-subtitle">{total} registered users</p>
        </div>
        <button type="button" className="admin-btn primary" onClick={() => void exportCsv()}>
          Export CSV
        </button>
      </header>

      <div className="admin-toolbar">
        <input
          className="admin-input"
          placeholder="Search name or email…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select className="admin-select" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
        <select className="admin-select" value={licenseFilter} onChange={(e) => { setLicenseFilter(e.target.value); setPage(1) }}>
          <option value="">All licenses</option>
          <option value="trial_active">Trial Active</option>
          <option value="trial_expired">Trial Expired</option>
          <option value="lifetime">Lifetime</option>
        </select>
      </div>

      {error && <div className="admin-error">{error}</div>}
      {loading && !items.length ? <div className="admin-loading">Loading users…</div> : (
        <div className="admin-panel">
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>License</th>
                  <th>Payment</th>
                  <th>Status</th>
                  <th>Registered</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.full_name}</td>
                    <td>{u.email}</td>
                    <td>{u.role}</td>
                    <td>{u.license_type}</td>
                    <td>{statusBadge(u.payment_status)}</td>
                    <td>{statusBadge(u.account_status)}</td>
                    <td>{new Date(u.registration_date).toLocaleDateString()}</td>
                    <td>
                      <div className="admin-action-group">
                        <select
                          className="admin-select"
                          defaultValue=""
                          onChange={(e) => {
                            const val = e.target.value as LicenseOverrideType
                            if (val) void handleAction('set-license', u.id, val)
                            e.target.value = ''
                          }}
                        >
                          <option value="">Set license…</option>
                          <option value="guest">Guest</option>
                          <option value="trial">Trial</option>
                          <option value="premium">Premium</option>
                          <option value="lifetime">Lifetime</option>
                          <option value="expired">Expired</option>
                          <option value="suspended">Suspended</option>
                        </select>
                        <button type="button" className="admin-btn" onClick={() => void handleAction('reset', u.id)}>Reset Trial</button>
                        <button type="button" className="admin-btn" onClick={() => void handleAction('activate', u.id)}>Activate</button>
                        <button type="button" className="admin-btn" onClick={() => void handleAction('suspend', u.id)}>Suspend</button>
                        <button type="button" className="admin-btn danger" onClick={() => void handleAction('delete', u.id)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="admin-pagination">
            <button type="button" className="admin-btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
            <span>Page {page} of {totalPages}</span>
            <button type="button" className="admin-btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
