import { useCallback, useEffect, useRef, useState } from 'react'
import { getWsBase } from '../api/client'
import type { InspectionSession, Platform } from '../types'

interface LiveRefreshOptions {
  deviceId: string | null
  platform: Platform
  enabled: boolean
  interval?: number
  onSessionUpdate: (session: InspectionSession) => void
  onError?: (message: string) => void
  onStatusChange?: (connected: boolean) => void
}

export function useLiveRefresh({
  deviceId,
  platform,
  enabled,
  interval = 2,
  onSessionUpdate,
  onError,
  onStatusChange,
}: LiveRefreshOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const callbacksRef = useRef({ onSessionUpdate, onError, onStatusChange })
  callbacksRef.current = { onSessionUpdate, onError, onStatusChange }

  const disconnect = useCallback(() => {
    const ws = wsRef.current
    if (ws) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'unsubscribe' }))
      }
      ws.close()
      wsRef.current = null
    }
    setConnected(false)
    callbacksRef.current.onStatusChange?.(false)
  }, [])

  useEffect(() => {
    if (!enabled || !deviceId) {
      disconnect()
      return
    }

    const ws = new WebSocket(`${getWsBase()}/ws/live`)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      callbacksRef.current.onStatusChange?.(true)
      ws.send(JSON.stringify({
        action: 'subscribe',
        device_id: deviceId,
        platform,
        interval,
      }))
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'session_update' && msg.session) {
          callbacksRef.current.onSessionUpdate(msg.session as InspectionSession)
        } else if (msg.type === 'error') {
          callbacksRef.current.onError?.(msg.message)
        }
      } catch {
        callbacksRef.current.onError?.('Invalid WebSocket message')
      }
    }

    ws.onerror = () => {
      callbacksRef.current.onError?.('WebSocket connection error')
    }

    ws.onclose = () => {
      setConnected(false)
      callbacksRef.current.onStatusChange?.(false)
    }

    return () => {
      disconnect()
    }
  }, [enabled, deviceId, platform, interval, disconnect])

  return { connected, disconnect }
}
