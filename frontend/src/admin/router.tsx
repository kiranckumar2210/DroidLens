import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import AdminDashboard from './AdminDashboard'
import AdminUsers from './AdminUsers'
import AdminPayments from './AdminPayments'
import AdminSubscriptions from './AdminSubscriptions'
import AdminRevenue from './AdminRevenue'
import AdminActivity from './AdminActivity'
import AdminSystemSettings from './AdminSystemSettings'

interface RouterContextValue {
  path: string
  navigate: (to: string) => void
}

const RouterContext = createContext<RouterContextValue | null>(null)

function useRouter() {
  const ctx = useContext(RouterContext)
  if (!ctx) throw new Error('Router hooks must be used within AdminRouter')
  return ctx
}

export function AdminRouter({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(() => window.location.pathname)

  const navigate = useCallback((to: string) => {
    if (to !== window.location.pathname) {
      window.history.pushState({}, '', to)
    }
    setPath(to)
  }, [])

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const value = useMemo(() => ({ path, navigate }), [path, navigate])
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
}

export function NavLink({
  to,
  end,
  className,
  children,
}: {
  to: string
  end?: boolean
  className: string
  children: ReactNode
}) {
  const { path, navigate } = useRouter()
  const active = end ? path === to : path.startsWith(to)
  return (
    <button
      type="button"
      className={`${className}${active ? ' active' : ''}`}
      onClick={() => navigate(to)}
    >
      {children}
    </button>
  )
}

export function Outlet() {
  const { path } = useRouter()
  if (path === '/admin' || path === '/admin/') {
    return <AdminDashboard />
  }
  if (path.startsWith('/admin/users')) {
    return <AdminUsers />
  }
  if (path.startsWith('/admin/payments')) {
    return <AdminPayments />
  }
  if (path.startsWith('/admin/subscriptions')) {
    return <AdminSubscriptions />
  }
  if (path.startsWith('/admin/revenue')) {
    return <AdminRevenue />
  }
  if (path.startsWith('/admin/activity')) {
    return <AdminActivity />
  }
  if (path.startsWith('/admin/settings')) {
    return <AdminSystemSettings />
  }
  return <AdminDashboard />
}
