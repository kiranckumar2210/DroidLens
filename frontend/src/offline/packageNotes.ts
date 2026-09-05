/** Per-package notes stored locally (keyed by path or label). */

const STORAGE_KEY = 'droidlens-package-notes-v1'

function loadAll(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') as Record<string, string>
  } catch {
    return {}
  }
}

export function packageNoteKey(pair: { xmlPath?: string; label: string }): string {
  return pair.xmlPath ?? pair.label
}

export function loadPackageNote(pair: { xmlPath?: string; label: string }): string {
  return loadAll()[packageNoteKey(pair)] ?? ''
}

export function savePackageNote(pair: { xmlPath?: string; label: string }, note: string): void {
  const key = packageNoteKey(pair)
  const all = loadAll()
  if (note.trim()) all[key] = note.trim()
  else delete all[key]
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
}
