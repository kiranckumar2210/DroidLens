import {
  Cpu, Layers, Maximize2, Monitor, Smartphone, Wifi,
} from 'lucide-react'
import type { AdbStatus, DeviceInfo, InspectionSession } from '../types'
import type { ThemeMode } from '../hooks/useTheme'

interface Props {
  adb: AdbStatus | null
  device: DeviceInfo | null
  session: InspectionSession | null
  sessionKind: 'live' | 'offline' | 'mock'
  theme: ThemeMode
  zoom: number
  coords: { x: number; y: number } | null
  elementCount: number
  message: string
  licenseLabel?: string | null
  onLicenseClick?: () => void
}

export default function StatusBar({
  adb, device, session, sessionKind, theme, zoom, coords, elementCount, message,
  licenseLabel, onLicenseClick,
}: Props) {
  const adbLabel = !adb ? 'ADB —' : adb.installed
    ? `ADB · ${adb.device_count} device${adb.device_count === 1 ? '' : 's'}`
    : 'ADB not found'

  const modeLabel = sessionKind === 'live' ? 'Live'
    : sessionKind === 'offline' ? 'Offline'
    : 'Sample'

  return (
    <footer className="status-bar">
      <div className="status-group">
        <span className={`status-item ${adb?.installed ? 'ok' : 'err'}`} title="ADB status">
          <Wifi size={12} /> {adbLabel}
        </span>
        <span className="status-sep" />
        <span className="status-item" title="Connected device">
          <Smartphone size={12} />
          {device?.name || session?.device_id || 'No device'}
        </span>
        {device?.os_version && (
          <>
            <span className="status-sep" />
            <span className="status-item" title="Android version">
              <Monitor size={12} /> Android {device.os_version}
            </span>
          </>
        )}
        <span className="status-sep" />
        <span className={`status-item mode-${sessionKind}`} title="Inspection mode">
          <Cpu size={12} /> {modeLabel}
        </span>
      </div>

      <div className="status-group status-center">
        <span className="status-message">{message}</span>
      </div>

      <div className="status-group status-end">
        {licenseLabel && (
          <>
            <button
              type="button"
              className={`status-item status-license ${licenseLabel.includes('Trial') ? 'trial' : licenseLabel.includes('Lifetime') ? 'lifetime' : ''}`}
              title="Account & license"
              onClick={onLicenseClick}
            >
              {licenseLabel}
            </button>
            <span className="status-sep" />
          </>
        )}
        <span className="status-item" title="Elements in hierarchy">
          <Layers size={12} /> {elementCount} elements
        </span>
        <span className="status-sep" />
        <span className="status-item" title="Screenshot zoom">
          <Maximize2 size={12} /> {Math.round(zoom * 100)}%
        </span>
        {coords && (
          <>
            <span className="status-sep" />
            <span className="status-item mono" title="Cursor coordinates">
              {coords.x}, {coords.y}
            </span>
          </>
        )}
        <span className="status-sep" />
        <span className="status-item capitalize" title="Theme">{theme}</span>
        {session?.screen_width && (
          <>
            <span className="status-sep" />
            <span className="status-item mono" title="Screen resolution">
              {session.screenshot_width || session.screen_width}×{session.screenshot_height || session.screen_height}
            </span>
          </>
        )}
      </div>
    </footer>
  )
}
