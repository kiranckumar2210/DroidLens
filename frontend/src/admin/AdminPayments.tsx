import { useCallback, useEffect, useState } from 'react'
import { adminApi, formatInr } from './api'
import type { AdminPaymentRow } from './api'

function statusBadge(status: string) {
  const cls = status === 'completed' ? 'success'
    : status === 'failed' || status === 'refunded' ? 'danger'
      : status === 'pending' || status === 'created' ? 'warning' : 'neutral'
  return <span className={`admin-badge ${cls}`}>{status}</span>
}

export default function AdminPayments() {
  const [items, setItems] = useState<AdminPaymentRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const pageSize = 15

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await adminApi.listPayments({
        page,
        page_size: pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
      })
      setItems(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => { void load() }, 45_000)
    return () => window.clearInterval(id)
  }, [load])

  const exportCsv = async () => {
    const csv = await adminApi.exportPayments({
      search: search || undefined,
      status: statusFilter || undefined,
    })
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'payments.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div>
      <header className="admin-page-header">
        <div>
          <h1>Payments</h1>
          <p className="admin-subtitle">{total} orders</p>
        </div>
        <button type="button" className="admin-btn primary" onClick={() => void exportCsv()}>
          Export CSV
        </button>
      </header>

      <div className="admin-toolbar">
        <input
          className="admin-input"
          placeholder="Search order, email…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
        />
        <select className="admin-select" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
          <option value="refunded">Refunded</option>
        </select>
      </div>

      {loading && !items.length ? <div className="admin-loading">Loading payments…</div> : (
        <div className="admin-panel">
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>User</th>
                  <th>Amount</th>
                  <th>Provider</th>
                  <th>Plan</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{p.order_id}</td>
                    <td>{p.user_email}</td>
                    <td>{formatInr(p.amount_inr)}</td>
                    <td>{p.payment_provider}</td>
                    <td>{p.plan_id}</td>
                    <td>{statusBadge(p.status)}</td>
                    <td>{new Date(p.created_at).toLocaleString()}</td>
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
