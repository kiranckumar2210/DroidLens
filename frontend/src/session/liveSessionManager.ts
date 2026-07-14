/** Live inspection session recovery and diagnostic logging. */

import { withTimeout } from '../utils/withTimeout'
import { api } from '../api/client'
import type { InspectionSession } from '../types'
import type { SessionKind } from './storage'

export type LiveSessionEvent =
  | 'record_clicked'
  | 'recording_initialized'
  | 'recording_failed'
  | 'recording_stopped'
  | 'recording_cancelled'
  | 'live_session_preserved'
  | 'device_connection_verified'
  | 'session_restore_attempt'
  | 'session_restored'
  | 'session_reconnect_attempt'
  | 'session_reconnected'
  | 'session_restore_failed'
  | 'xml_refreshed'
  | 'screenshot_refreshed'

export function liveSessionLog(event: LiveSessionEvent, detail?: Record<string, unknown>): void {
  const payload = detail ? ` ${JSON.stringify(detail)}` : ''
  console.info(`[LiveSession] ${event}${payload}`)
}

export interface RestoreLiveSessionOptions {
  deviceId: string
  sessionKind: SessionKind
  packageName?: string
}

/**
 * Restore an existing backend session or reconnect live when the in-memory session was lost.
 * Never navigates — returns session data for the caller to apply.
 */
export async function restoreLiveSession(
  opts: RestoreLiveSessionOptions,
): Promise<InspectionSession> {
  const { deviceId, sessionKind, packageName } = opts
  liveSessionLog('session_restore_attempt', { deviceId, sessionKind })

  try {
    let session = await withTimeout(api.getSession(deviceId), 15000, 'Load session')
    liveSessionLog('session_restored', { deviceId, mode: session.mode })

    if (sessionKind === 'live' && session.mode === 'live') {
      try {
        session = await withTimeout(api.refreshSessionWithRetry(deviceId), 45000, 'Refresh session')
        liveSessionLog('xml_refreshed', { deviceId, ms: session.last_refresh_ms })
        liveSessionLog('screenshot_refreshed', { deviceId })
      } catch (err) {
        liveSessionLog('session_restored', {
          deviceId,
          refreshSkipped: true,
          reason: (err as Error).message,
        })
      }
    }
    return session
  } catch {
    if (sessionKind !== 'live') {
      liveSessionLog('session_restore_failed', { deviceId, sessionKind })
      throw new Error('Offline session no longer available')
    }

    liveSessionLog('session_reconnect_attempt', { deviceId })
    try {
      await withTimeout(api.listDevices(true), 15000, 'List devices')
      liveSessionLog('device_connection_verified', { deviceId })
    } catch {
      /* device list optional */
    }

    await withTimeout(
      api.connect(deviceId, 'android', packageName || undefined),
      45000,
      'Reconnect device',
    )
    const session = await withTimeout(api.refreshSessionWithRetry(deviceId), 45000, 'Refresh after reconnect')
    liveSessionLog('session_reconnected', { deviceId, ms: session.last_refresh_ms })
    return session
  }
}
