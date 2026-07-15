/** Lightweight recent XML file paths — no database, no file copies. */

export interface RecentFileEntry {
  xmlName: string
  xmlPath?: string
  screenshotPath?: string
  openedAt: string
}

const STORAGE_KEY = 'droidlens-recent-xml-files-v1'
const MAX = 12

export function loadRecentFiles(): RecentFileEntry[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as RecentFileEntry[]
  } catch {
    return []
  }
}

export function addRecentFile(entry: Omit<RecentFileEntry, 'openedAt'>): void {
  const next: RecentFileEntry = { ...entry, openedAt: new Date().toISOString() }
  const list = loadRecentFiles().filter(
    (r) => r.xmlPath !== entry.xmlPath || r.xmlName !== entry.xmlName,
  )
  list.unshift(next)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX)))
}

export function clearRecentFiles(): void {
  localStorage.removeItem(STORAGE_KEY)
}
