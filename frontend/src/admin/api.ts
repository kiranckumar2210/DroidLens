import { loadAuthToken } from '../auth/tokenStorage'
import { getApiBase } from '../api/baseUrl'

async function adminRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const token = loadAuthToken()
  const res = await fetch(`${getApiBase()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
  }
  return res.json()
}

export interface AdminKpis {
  total_registered_users: number
  active_trial_users: number
  lifetime_subscribers: number
  guest_sessions_today: number
  total_revenue_inr: number
  trial_conversion_rate: number
  payments_today: number
  active_sessions: number
}

export interface AdminDashboard {
  kpis: AdminKpis
  registration: {
    today: number
    yesterday: number
    this_week: number
    this_month: number
    total: number
    period: string
    daily: { date: string; count: number }[]
  }
  revenue: {
    today_inr: number
    week_inr: number
    month_inr: number
    total_inr: number
    arpu_inr: number
    period: string
  }
  payments: {
    total_orders: number
    successful: number
    failed: number
    pending: number
    refunded: number
    success_rate: number
  }
  subscriptions: {
    trial_active: number
    trial_expired: number
    lifetime_users: number
    conversion_rate: number
  }
  recent_users: AdminUserRow[]
  recent_payments: AdminPaymentRow[]
  recent_activity: ActivityEvent[]
  updated_at: string
}

export interface AdminUserRow {
  id: string
  full_name: string
  email: string
  role: string
  registration_date: string
  license_type: string
  license_status: string
  trial_status: string
  payment_status: string
  last_login?: string | null
  account_status: string
}

export interface AdminPaymentRow {
  id: string
  order_id: string
  transaction_id?: string | null
  user_id: string
  user_name: string
  user_email: string
  amount_inr: number
  currency: string
  payment_provider: string
  payment_method?: string | null
  status: string
  plan_id: string
  created_at: string
  completed_at?: string | null
}

export interface ActivityEvent {
  id: string
  timestamp: string
  user_id?: string | null
  user_email?: string | null
  action: string
  status: string
  detail?: string | null
}

export interface PaginatedUsers {
  items: AdminUserRow[]
  total: number
  page: number
  page_size: number
}

export interface PaginatedPayments {
  items: AdminPaymentRow[]
  total: number
  page: number
  page_size: number
}

export type LicenseOverrideType = import('../auth/types').LicenseOverrideType

export interface LicensingSettings {
  subscription: {
    subscription_enabled: boolean
    trial_enabled: boolean
    guest_access_enabled: boolean
    login_required_for_live: boolean
  }
  payment: {
    payment_enabled: boolean
    trial_days: number
    lifetime_price_inr: number
    currency: string
    discount_percent: number
    promotional_message: string
  }
  features: import('../auth/types').FeatureFlags
  updated_at?: string | null
}

export function formatInr(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

export const adminApi = {
  dashboard: () => adminRequest<AdminDashboard>('/admin/dashboard'),

  listUsers: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') qs.set(k, String(v))
    })
    return adminRequest<PaginatedUsers>(`/admin/users?${qs}`)
  },

  listPayments: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') qs.set(k, String(v))
    })
    return adminRequest<PaginatedPayments>(`/admin/payments?${qs}`)
  },

  revenue: (period = '30d') =>
    adminRequest<AdminDashboard['revenue']>(`/admin/revenue?period=${period}`),

  subscriptions: () =>
    adminRequest<AdminDashboard['subscriptions']>('/admin/subscriptions'),

  activity: (page = 1, pageSize = 50) =>
    adminRequest<{ items: ActivityEvent[]; total: number; page: number; page_size: number }>(
      `/admin/activity?page=${page}&page_size=${pageSize}`,
    ),

  statistics: () => adminRequest<Record<string, unknown>>('/admin/statistics'),

  suspendUser: (userId: string) =>
    adminRequest<{ ok: boolean; message: string }>(`/admin/users/${userId}/suspend`, { method: 'POST' }),

  resetTrial: (userId: string) =>
    adminRequest<{ ok: boolean; message: string }>(`/admin/users/${userId}/reset-trial`, { method: 'POST' }),

  activateLicense: (userId: string) =>
    adminRequest<{ ok: boolean; message: string }>(`/admin/users/${userId}/activate-license`, { method: 'POST' }),

  setLicense: (userId: string, licenseType: LicenseOverrideType) =>
    adminRequest<{ ok: boolean; message: string }>(`/admin/users/${userId}/set-license`, {
      method: 'POST',
      body: JSON.stringify({ license_type: licenseType }),
    }),

  getLicensingSettings: () =>
    adminRequest<LicensingSettings>('/admin/settings/licensing'),

  updateLicensingSettings: (payload: Record<string, unknown>) =>
    adminRequest<LicensingSettings>('/admin/settings/licensing', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  deleteUser: (userId: string) =>
    adminRequest<{ ok: boolean; message: string }>(`/admin/users/${userId}`, { method: 'DELETE' }),

  exportUsers: async (params: Record<string, string | undefined> = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v) })
    const token = loadAuthToken()
    const res = await fetch(`${getApiBase()}/admin/users/export?${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Export failed')
    return res.text()
  },

  exportPayments: async (params: Record<string, string | undefined> = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v) })
    const token = loadAuthToken()
    const res = await fetch(`${getApiBase()}/admin/payments/export?${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Export failed')
    return res.text()
  },
}
