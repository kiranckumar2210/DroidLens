import { useCallback, useEffect, useState } from 'react'
import { adminApi } from './api'
import type { ActivityEvent } from './api'

export default function AdminActivity() {
  const [items, setItems] = useState<ActivityEvent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const pageSize = 50

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await adminApi.activity(page, pageSize)
      setItems(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    void load()
    const id = window.setInterval(() => { void load() }, 45_000)
    return () => window.clearInterval(id)
  }, [load])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div>
      <header className="admin-page-header">
        <div>
          <h1>Activity Logs</h1>
          <p className="admin-subtitle">{total} audit events</p>
        </div>
        <span className="admin-refresh-hint">Auto-refreshes every 45s</span>
      </header>

      {loading && !items.length ? <div className="admin-loading">Loading activity…</div> : (
        <div className="admin-panel">
          <ul className="admin-activity-list">
            {items.map((e) => (
              <li key={e.id} className="admin-activity-item">
                <time>{new Date(e.timestamp).toLocaleString()}</time>
                <span>
                  <strong>{e.action}</strong>
                  {e.user_email && ` · ${e.user_email}`}
                  {e.detail && <em> — {e.detail}</em>}
                  {' '}
                  <span className={`admin-badge ${e.status === 'success' ? 'success' : 'danger'}`}>{e.status}</span>
                </span>
              </li>
            ))}
          </ul>
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
