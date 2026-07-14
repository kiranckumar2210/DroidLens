import { useAuth } from '../auth/AuthContext'
import AccessDenied from './AccessDenied'
import AdminLayout from './AdminLayout'
import { AdminRouter } from './router'
import './admin.css'

export default function AdminApp() {
  const { loading, isAdmin, isLoggedIn } = useAuth()

  if (loading) {
    return <div className="admin-loading" style={{ minHeight: '100vh' }}>Loading…</div>
  }

  if (!isLoggedIn || !isAdmin) {
    return <AccessDenied />
  }

  return (
    <AdminRouter>
      <AdminLayout />
    </AdminRouter>
  )
}
