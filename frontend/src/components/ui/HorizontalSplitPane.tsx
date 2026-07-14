import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

interface Props {
  initialPercent?: number
  minPercent?: number
  maxPercent?: number
  children: [ReactNode, ReactNode]
  className?: string
}

/** Vertical divider — left/right split by percentage width. */
export function HorizontalSplitPane({
  initialPercent = 50,
  minPercent = 25,
  maxPercent = 75,
  children,
  className = '',
}: Props) {
  const [leftPct, setLeftPct] = useState(initialPercent)
  const dragging = useRef(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const onMove = useCallback((e: MouseEvent) => {
    if (!dragging.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const pct = ((e.clientX - rect.left) / rect.width) * 100
    setLeftPct(Math.min(maxPercent, Math.max(minPercent, pct)))
  }, [minPercent, maxPercent])

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

  const [left, right] = children

  return (
    <div ref={containerRef} className={`h-split-pane ${className}`}>
      <div className="h-split-left" style={{ width: `${leftPct}%` }}>
        {left}
      </div>
      <div
        className="h-split-handle"
        onMouseDown={() => {
          dragging.current = true
          document.body.classList.add('is-resizing')
        }}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize panels"
      />
      <div className="h-split-right" style={{ width: `${100 - leftPct}%` }}>
        {right}
      </div>
    </div>
  )
}
