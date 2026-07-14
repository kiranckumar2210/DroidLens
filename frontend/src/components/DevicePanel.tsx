import { RefreshCw, Wifi } from 'lucide-react'
import type { AdbStatus, DeviceInfo } from '../types'

interface Props {
  devices: DeviceInfo[]
  deviceId: string
  adb: AdbStatus | null
  mockMode: boolean
  embedded?: boolean
  onSelect: (id: string) => void
  onRefresh: () => void
  onRestartAdb: () => void
  wifiHost: string
  onWifiHostChange: (v: string) => void
  onWifiConnect: () => void
}

export default function DevicePanel({
  devices, deviceId, adb, mockMode, embedded = false, onSelect, onRefresh, onRestartAdb,
  wifiHost, onWifiHostChange, onWifiConnect,
}: Props) {
  const selected = devices.find((d) => d.id === deviceId)

  return (
    <div className={`panel device-panel ${embedded ? 'device-panel-compact' : ''}`}>
      <div className="panel-header">
        {embedded ? 'Device' : 'Device Manager'}
        <button className="copy-btn" onClick={onRefresh} title="Refresh devices">
          <RefreshCw size={12} />
        </button>
      </div>
      <div className="device-panel-body">
        {adb && (
          <div className="adb-status">
            <div className="adb-row">
              <span>ADB</span>
              <span className={adb.installed ? 'ok' : 'err'}>
                {adb.installed ? adb.version?.slice(0, 30) : 'Not installed'}
              </span>
            </div>
            <div className="adb-row">
              <span>Devices</span>
              <span>{adb.device_count} online</span>
            </div>
            {adb.unauthorized_count > 0 && (
              <div className="adb-warn">⚠ {adb.unauthorized_count} unauthorized — accept USB debugging</div>
            )}
            {adb.offline_count > 0 && (
              <div className="adb-warn">⚠ {adb.offline_count} offline</div>
            )}
            <button className="copy-btn" onClick={onRestartAdb}>Restart ADB</button>
          </div>
        )}

        <label className="field-label">Active Device</label>
        <select value={deviceId} onChange={(e) => onSelect(e.target.value)} className="full-width">
          {devices.length === 0 && <option value="">No devices</option>}
          {devices.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} [{d.connection_type}]
            </option>
          ))}
        </select>

        {selected && (
          <div className="device-details">
            <Detail label="Model" value={selected.model} />
            <Detail label="Manufacturer" value={selected.manufacturer} />
            <Detail label="Android" value={selected.os_version} />
            <Detail label="SDK" value={selected.sdk_version} />
            <Detail label="Resolution" value={selected.resolution} />
            <Detail label="Orientation" value={selected.orientation} />
            <Detail label="Battery" value={selected.battery_level != null ? `${selected.battery_level}%` : undefined} />
            <Detail label="Serial" value={selected.serial} />
            <Detail label="Type" value={selected.is_emulator ? 'Emulator' : 'Physical'} />
            <Detail label="Connection" value={selected.connection_type} />
          </div>
        )}

        {!mockMode && (
          <div className="wifi-connect">
            <label className="field-label"><Wifi size={12} /> WiFi ADB</label>
            <div className="wifi-row">
              <input
                placeholder="192.168.1.100"
                value={wifiHost}
                onChange={(e) => onWifiHostChange(e.target.value)}
              />
              <button onClick={onWifiConnect}>Connect</button>
            </div>
          </div>
        )}

        {mockMode && <div className="adb-warn">Mock mode — set DROIDLENS_MOCK=false for real devices</div>}
      </div>
    </div>
  )
}

function Detail({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return (
    <div className="detail-row">
      <span>{label}</span>
      <span className="mono">{value}</span>
    </div>
  )
}
