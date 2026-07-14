import { NavLink, Outlet } from './router'
import { useAuth } from '../auth/AuthContext'
import BrandLogo from '../components/BrandLogo'
import './admin.css'

const NAV = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/payments', label: 'Payments' },
  { to: '/admin/subscriptions', label: 'Subscriptions' },
  { to: '/admin/revenue', label: 'Revenue' },
  { to: '/admin/activity', label: 'Activity Logs' },
]

const SETTINGS_NAV = [
  { to: '/admin/settings', label: 'Licensing & Subscription' },
]

export default function AdminLayout() {
  const { user } = useAuth()

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <BrandLogo size={28} />
          <div>
            <strong>DroidLens</strong>
            <span>Admin</span>
          </div>
        </div>
        <nav className="admin-nav">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className="admin-nav-link">
              {item.label}
            </NavLink>
          ))}
          <div className="admin-nav-section">System Settings</div>
          {SETTINGS_NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className="admin-nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <a href="/" className="admin-back-link">← Back to App</a>
          {user && <p className="admin-user-meta">{user.full_name}</p>}
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  )
}
