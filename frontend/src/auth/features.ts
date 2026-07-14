import type { AppFeature, LicenseInfo, PremiumFeature, SystemConfig, UserTier } from './types'

const PREMIUM_FEATURES: PremiumFeature[] = [
  'live_inspection',
  'xml_upload',
  'screenshot_upload',
  'code_generator',
  'locator_builder',
  'custom_locator_builder',
  'locator_repository',
  'export',
  'session_save',
  'ai_locator_suggestions',
  'plugin_marketplace',
  'interaction_recorder',
]

const GUEST_ALLOWED: AppFeature[] = ['mock_demo', 'settings', 'documentation', 'about']

const FEATURE_TO_FLAG: Partial<Record<PremiumFeature, keyof SystemConfig['features']>> = {
  live_inspection: 'live_inspector',
  xml_upload: 'xml_upload',
  screenshot_upload: 'screenshot_upload',
  code_generator: 'code_generator',
  locator_builder: 'locator_builder',
  custom_locator_builder: 'locator_builder',
  export: 'export',
  interaction_recorder: 'recorder',
  ai_locator_suggestions: 'ai_features',
  session_save: 'session_manager',
}

const FEATURE_LABELS: Record<PremiumFeature, string> = {
  live_inspection: 'Live Device Inspection',
  xml_upload: 'XML Upload',
  screenshot_upload: 'Screenshot Upload',
  code_generator: 'Code Generator',
  locator_builder: 'Locator Builder',
  custom_locator_builder: 'Custom Locator Builder',
  locator_repository: 'Locator Repository',
  export: 'Export',
  session_save: 'Session Saving',
  ai_locator_suggestions: 'AI Locator Suggestions',
  plugin_marketplace: 'Plugin Marketplace',
  interaction_recorder: 'Smart Interaction Recorder',
}

export function featureLabel(feature: PremiumFeature): string {
  return FEATURE_LABELS[feature] ?? feature
}

export function resolveUserTier(
  isLoggedIn: boolean,
  license: LicenseInfo | null,
): UserTier {
  if (!isLoggedIn || !license) return 'guest'
  if (license.has_premium) {
    return license.status === 'lifetime' || license.status === 'subscription_active'
      ? 'licensed'
      : 'trial'
  }
  return 'guest'
}

export interface AccessResult {
  allowed: boolean
  reason?: 'guest' | 'login_required' | 'trial_expired' | 'license_required'
  message?: string
}

export class FeatureAccessManager {
  static canAccess(
    feature: AppFeature,
    isLoggedIn: boolean,
    license: LicenseInfo | null,
    systemConfig?: SystemConfig | null,
  ): AccessResult {
    if (GUEST_ALLOWED.includes(feature)) {
      if (systemConfig && !systemConfig.guest_access_enabled && !isLoggedIn) {
        return {
          allowed: false,
          reason: 'login_required',
          message: 'Guest access is disabled. Please sign in.',
        }
      }
      return { allowed: true }
    }

    if (!PREMIUM_FEATURES.includes(feature as PremiumFeature)) {
      return { allowed: true }
    }

    const premium = feature as PremiumFeature
    const flagKey = FEATURE_TO_FLAG[premium]
    if (systemConfig && flagKey && !systemConfig.features[flagKey]) {
      return {
        allowed: false,
        reason: 'license_required',
        message: `${featureLabel(premium)} is currently disabled by the administrator.`,
      }
    }

    if (systemConfig && !systemConfig.subscription_enabled) {
      if (!isLoggedIn) {
        return {
          allowed: false,
          reason: 'login_required',
          message: `${featureLabel(premium)} requires an account. Sign in to continue.`,
        }
      }
      return { allowed: true }
    }

    if (!isLoggedIn) {
      return {
        allowed: false,
        reason: 'login_required',
        message: `${featureLabel(premium)} requires an account. Sign in or start your free ${systemConfig?.trial_days ?? 7}-day trial.`,
      }
    }

    if (!license?.has_premium) {
      if (license?.status === 'payment_pending') {
        return {
          allowed: false,
          reason: 'license_required',
          message: `Payment is pending. Complete your purchase to unlock ${featureLabel(premium)}.`,
        }
      }
      if (license?.status === 'trial_expired') {
        return {
          allowed: false,
          reason: 'trial_expired',
          message: `Your free trial has ended. Purchase a Lifetime License to unlock ${featureLabel(premium)}.`,
        }
      }
      return {
        allowed: false,
        reason: 'license_required',
        message: `${featureLabel(premium)} requires an active license.`,
      }
    }

    return { allowed: true }
  }

  static isPremiumFeature(feature: AppFeature): feature is PremiumFeature {
    return PREMIUM_FEATURES.includes(feature as PremiumFeature)
  }
}

export function trialBannerText(
  license: LicenseInfo | null,
  subscriptionEnabled = true,
): string | null {
  if (!subscriptionEnabled) return null
  if (!license || license.status !== 'trial_active') return null
  const days = license.days_remaining ?? 0
  return `Trial Active — ${days} day${days === 1 ? '' : 's'} remaining`
}

export function licenseBadgeText(
  license: LicenseInfo | null,
  isLoggedIn: boolean,
  subscriptionEnabled = true,
): string | null {
  if (!isLoggedIn || !license) return 'Guest'
  if (!subscriptionEnabled) return 'Premium'
  if (license.status === 'lifetime') return 'Lifetime License'
  if (license.status === 'payment_pending') return 'Payment Pending'
  if (license.status === 'trial_active') {
    return `Trial · ${license.days_remaining ?? 0}d left`
  }
  if (license.status === 'trial_expired') return 'Trial Expired'
  return license.plan_name
}

export function dashboardStatusText(
  license: LicenseInfo | null,
  isLoggedIn: boolean,
  subscriptionEnabled = true,
): string | null {
  if (!subscriptionEnabled) {
    if (!isLoggedIn) return null
    return '✅ Premium Access (Development Mode)'
  }
  if (!isLoggedIn || !license) return '🔒 Premium Locked'
  if (license.status === 'lifetime') return '✅ Lifetime Activated'
  if (license.status === 'payment_pending') return '⌛ Payment Pending'
  if (license.status === 'trial_active') {
    const days = license.days_remaining ?? 0
    return `🎉 Trial Active — ${days} day${days === 1 ? '' : 's'} remaining`
  }
  if (license.status === 'trial_expired') return '⚠ Trial Expired'
  return '🔒 Premium Locked'
}
