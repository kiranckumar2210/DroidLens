import { RefreshCw, RotateCcw, Home } from 'lucide-react'
import { resetApplicationState } from '../session/resetState'

interface Props {
  restoring: boolean
  restoreError: string | null
  deviceId: string
  onRetry: () => void
  onReconnect: () => void
  onDashboard: () => void
  onReset: () => void
}

export default function SessionRecoveryBanner({
  restoring,
  restoreError,
  deviceId,
  onRetry,
  onReconnect,
  onDashboard,
  onReset,
}: Props) {
  return (
    <div className="session-recovery-banner" role="alert">
      <div className="session-recovery-content">
        {restoring ? (
          <>
            <RefreshCw size={20} className="spin" />
            <div>
              <strong>Restoring live session…</strong>
              <p>Reconnecting to {deviceId || 'device'}. The inspector will appear shortly.</p>
            </div>
          </>
        ) : (
          <>
            <RotateCcw size={20} />
            <div>
              <strong>Live session unavailable</strong>
              <p>
                {restoreError
                  || 'The inspection session was lost. Your device may still be connected via ADB.'}
              </p>
            </div>
          </>
        )}
      </div>
      {!restoring && (
        <div className="session-recovery-actions">
          <button type="button" className="btn-primary btn-sm" onClick={onRetry}>
            Retry restore
          </button>
          <button type="button" className="btn-secondary btn-sm" onClick={onReconnect}>
            Reconnect device
          </button>
          <button type="button" className="btn-secondary btn-sm" onClick={onDashboard}>
            <Home size={14} /> Dashboard
          </button>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => {
              resetApplicationState()
              onReset()
            }}
            title="Clear saved UI state (fixes stuck recorder)"
          >
            Reset UI
          </button>
        </div>
      )}
    </div>
  )
}
