/** Lightweight session history — live devices + offline files (paths only). */

import type { Platform } from '../types'

export type SessionHistoryKind = 'live' | 'offline' | 'mock'

export interface SessionHistoryEntry {
  id: string
  kind: SessionHistoryKind
  label: string
  platform?: Platform
  deviceId?: string
  packageName?: string
  xmlPath?: string
  screenshotPath?: string
  openedAt: string
}

const STORAGE_KEY = 'droidlens-session-history-v1'
const MAX = 15

export function loadSessionHistory(): SessionHistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as SessionHistoryEntry[]
  } catch {
    return []
  }
}

function entryKey(entry: Omit<SessionHistoryEntry, 'id' | 'openedAt'>): string {
  if (entry.kind === 'live') return `live:${entry.platform ?? 'android'}:${entry.deviceId}:${entry.packageName ?? ''}`
  if (entry.kind === 'offline') return `offline:${entry.xmlPath ?? entry.label}`
  return 'mock'
}

export function addSessionHistory(entry: Omit<SessionHistoryEntry, 'id' | 'openedAt'>): void {
  const id = entryKey(entry)
  const next: SessionHistoryEntry = { ...entry, id, openedAt: new Date().toISOString() }
  const list = loadSessionHistory().filter((h) => h.id !== id)
  list.unshift(next)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX)))
}

export function clearSessionHistory(): void {
  localStorage.removeItem(STORAGE_KEY)
}

export function removeSessionHistory(id: string): void {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(loadSessionHistory().filter((h) => h.id !== id)),
  )
}
