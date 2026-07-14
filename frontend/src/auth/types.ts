export type LicenseStatus =
  | 'guest'
  | 'trial_active'
  | 'trial_expired'
  | 'payment_pending'
  | 'lifetime'
  | 'subscription_active'
  | 'subscription_expired'

export type UserTier = 'guest' | 'trial' | 'licensed'

export interface AuthUser {
  id: string
  full_name: string
  email: string
  created_at: string
  avatar_url?: string | null
  last_login?: string | null
  status?: string
  role?: string
}

export interface LicenseInfo {
  status: LicenseStatus
  plan_id: string
  plan_name: string
  trial_started_at?: string | null
  trial_expires_at?: string | null
  license_activated_at?: string | null
  license_expires_at?: string | null
  days_remaining?: number | null
  has_premium: boolean
  price_inr?: number | null
  pending_payment_id?: string | null
  license_id?: string | null
}

export interface AuthSession {
  user: AuthUser
  license: LicenseInfo
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  refresh_expires_in?: number
  license_cache?: string | null
}

export interface OrderSummary {
  id: string
  order_id: string
  transaction_id?: string | null
  merchant_transaction_id?: string | null
  phonepe_transaction_id?: string | null
  amount_inr: number
  currency: string
  status: string
  payment_provider: string
  payment_method?: string | null
  plan_id: string
  created_at: string
  completed_at?: string | null
}

export interface AccountSummary {
  user: AuthUser
  license: LicenseInfo
  app_version: string
  purchase_history?: OrderSummary[]
  license_cache?: string | null
}

export interface PlanPublic {
  id: string
  name: string
  description: string
  price_inr?: number | null
  billing_period: string
  trial_days: number
  features: string[]
}

export interface PurchaseResult {
  payment_id: string
  order_id: string
  transaction_id: string
  plan_id: string
  plan_name: string
  amount_inr: number
  currency?: string
  status: string
  payment_provider?: string
  merchant_name: string
  customer_email?: string | null
  checkout_url?: string | null
}

export interface PricingResponse {
  lifetime_price_inr: number
  currency: string
  payment_provider: string
  trial_days: number
  plans: PlanPublic[]
}

export interface PaymentActionResult {
  payment_id: string
  status: string
  license: LicenseInfo
}

export interface OrderStatusResponse {
  payment_id: string
  order_id: string
  status: string
  payment_provider: string
  payment_method?: string | null
  phonepe_transaction_id?: string | null
  license: LicenseInfo
  checkout_url?: string | null
}

/** Premium capabilities — extend as new features ship */
export type PremiumFeature =
  | 'live_inspection'
  | 'xml_upload'
  | 'screenshot_upload'
  | 'code_generator'
  | 'locator_builder'
  | 'custom_locator_builder'
  | 'locator_repository'
  | 'export'
  | 'session_save'
  | 'ai_locator_suggestions'
  | 'plugin_marketplace'
  | 'interaction_recorder'

/** Always free for guests */
export type GuestFeature =
  | 'mock_demo'
  | 'settings'
  | 'documentation'
  | 'about'

export type AppFeature = PremiumFeature | GuestFeature

export interface FeatureFlags {
  mock_inspector: boolean
  live_inspector: boolean
  recorder: boolean
  xml_upload: boolean
  screenshot_upload: boolean
  locator_builder: boolean
  code_generator: boolean
  ai_features: boolean
  export: boolean
  device_manager: boolean
  session_manager: boolean
}

export interface SystemConfig {
  subscription_enabled: boolean
  payment_enabled: boolean
  trial_enabled: boolean
  guest_access_enabled: boolean
  login_required_for_live: boolean
  trial_days: number
  lifetime_price_inr: number
  currency: string
  discount_percent: number
  promotional_message: string
  features: FeatureFlags
}

export type LicenseOverrideType = 'guest' | 'trial' | 'premium' | 'lifetime' | 'expired' | 'suspended'
