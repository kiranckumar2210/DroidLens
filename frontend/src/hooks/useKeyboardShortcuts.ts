import { useEffect } from 'react'

export interface ShortcutHandlers {
  onRefresh?: () => void
  onFocusSearch?: () => void
  onExport?: () => void
  onToggleLiveRefresh?: () => void
  enabled?: boolean
}

/** Inspector keyboard shortcuts (v1.1). */
export function useKeyboardShortcuts({
  onRefresh,
  onFocusSearch,
  onExport,
  onToggleLiveRefresh,
  enabled = true,
}: ShortcutHandlers) {
  useEffect(() => {
    if (!enabled) return

    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const tag = target?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) return

      if (e.key === 'F5') {
        e.preventDefault()
        onRefresh?.()
        return
      }

      if (!(e.ctrlKey || e.metaKey)) return

      if (e.key === 'f' || e.key === 'F') {
        e.preventDefault()
        onFocusSearch?.()
        return
      }

      if (e.shiftKey && (e.key === 'e' || e.key === 'E')) {
        e.preventDefault()
        onExport?.()
        return
      }

      if (e.key === 'l' || e.key === 'L') {
        e.preventDefault()
        onToggleLiveRefresh?.()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [enabled, onRefresh, onFocusSearch, onExport, onToggleLiveRefresh])
}
