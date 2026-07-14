import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

interface Props {
  side: 'left' | 'right'
  initial: number
  min: number
  max: number
  children: ReactNode
  className?: string
}

export function SplitPane({ side, initial, min, max, children, className = '' }: Props) {
  const [width, setWidth] = useState(initial)
  const dragging = useRef(false)

  const onMove = useCallback((e: MouseEvent) => {
    if (!dragging.current) return
    const next = side === 'left' ? e.clientX : window.innerWidth - e.clientX
    setWidth(Math.min(max, Math.max(min, next)))
  }, [min, max, side])

  const onUp = useCallback(() => {
    dragging.current = false
    document.body.classList.remove('is-resizing')
  }, [])

  useEffect(() => {
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [onMove, onUp])

  return (
    <aside
      className={`split-pane split-pane-${side} ${className}`}
      style={{ width }}
    >
      {children}
      <div
        className={`split-handle split-handle-${side}`}
        onMouseDown={() => {
          dragging.current = true
          document.body.classList.add('is-resizing')
        }}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize panel"
      />
    </aside>
  )
}
