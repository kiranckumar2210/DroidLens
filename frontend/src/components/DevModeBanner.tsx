import { useAuth } from '../auth/AuthContext'
import { useSystemConfig } from '../auth/SystemConfigContext'

export default function DevModeBanner() {
  const { isAdmin } = useAuth()
  const { config } = useSystemConfig()

  if (!isAdmin || config.subscription_enabled) return null

  return (
    <div className="dev-mode-banner" role="status">
      <strong>Dev Mode</strong>
      <span>Subscription system is disabled — all authenticated users have premium access.</span>
    </div>
  )
}
