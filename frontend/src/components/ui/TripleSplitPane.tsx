import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

export interface StudioLayout {
  leftPct: number
  middlePct: number
  rightPct: number
  leftCollapsed: boolean
  middleCollapsed: boolean
  rightCollapsed: boolean
}

export const DEFAULT_STUDIO_LAYOUT: StudioLayout = {
  leftPct: 35,
  middlePct: 20,
  rightPct: 45,
  leftCollapsed: false,
  middleCollapsed: false,
  rightCollapsed: false,
}

const COLLAPSED_WIDTH = 36
const MIN_PCT = 12

interface Props {
  layout: StudioLayout
  onLayoutChange: (layout: StudioLayout) => void
  children: [ReactNode, ReactNode, ReactNode]
  className?: string
}

function normalize(left: number, middle: number, right: number): [number, number, number] {
  const l = Number(left)
  const m = Number(middle)
  const r = Number(right)
  const sum = l + m + r
  if (!Number.isFinite(sum) || sum <= 0) return [35, 20, 45]
  return [(l / sum) * 100, (m / sum) * 100, (r / sum) * 100]
}

/** Three resizable columns with collapse support. */
export function TripleSplitPane({ layout, onLayoutChange, children, className = '' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<'left' | 'right' | null>(null)

  const [leftPct, middlePct, rightPct] = normalize(layout.leftPct, layout.middlePct, layout.rightPct)

  const onMove = useCallback((e: MouseEvent) => {
    if (!dragRef.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const xPct = ((e.clientX - rect.left) / rect.width) * 100

    if (dragRef.current === 'left') {
      const newLeft = Math.min(70, Math.max(MIN_PCT, xPct))
      const remaining = 100 - newLeft
      const midRatio = middlePct / (middlePct + rightPct || 1)
      const newMiddle = remaining * midRatio
      const newRight = remaining - newMiddle
      onLayoutChange({
        ...layout,
        leftPct: newLeft,
        middlePct: newMiddle,
        rightPct: newRight,
        leftCollapsed: false,
      })
    } else {
      const splitAt = Math.min(88, Math.max(leftPct + MIN_PCT, xPct))
      const newMiddle = splitAt - leftPct
      const newRight = 100 - splitAt
      if (newMiddle >= MIN_PCT && newRight >= MIN_PCT) {
        onLayoutChange({
          ...layout,
          leftPct,
          middlePct: newMiddle,
          rightPct: newRight,
          middleCollapsed: false,
          rightCollapsed: false,
        })
      }
    }
  }, [layout, leftPct, middlePct, rightPct, onLayoutChange])

  const onUp = useCallback(() => {
    dragRef.current = null
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

  const [left, middle, right] = children

  const leftStyle = layout.leftCollapsed
    ? { width: COLLAPSED_WIDTH, flexShrink: 0 }
    : { width: `${leftPct}%`, flexShrink: 0 }

  const middleStyle = layout.middleCollapsed
    ? { width: COLLAPSED_WIDTH, flexShrink: 0 }
    : { width: `${middlePct}%`, flexShrink: 0 }

  const rightStyle = layout.rightCollapsed
    ? { width: COLLAPSED_WIDTH, flexShrink: 0 }
    : { width: `${rightPct}%`, flex: 1, minWidth: 0 }

  return (
    <div ref={containerRef} className={`triple-split-pane ${className}`}>
      <div className="triple-split-panel triple-split-left" style={leftStyle}>
        {left}
      </div>
      {!layout.leftCollapsed && !layout.middleCollapsed && (
        <div
          className="triple-split-handle"
          onMouseDown={() => { dragRef.current = 'left'; document.body.classList.add('is-resizing') }}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize screenshot and actions panels"
        />
      )}
      <div className="triple-split-panel triple-split-middle" style={middleStyle}>
        {middle}
      </div>
      {!layout.middleCollapsed && !layout.rightCollapsed && (
        <div
          className="triple-split-handle"
          onMouseDown={() => { dragRef.current = 'right'; document.body.classList.add('is-resizing') }}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize actions and code panels"
        />
      )}
      <div className="triple-split-panel triple-split-right" style={rightStyle}>
        {right}
      </div>
    </div>
  )
}

export function togglePanelCollapse(layout: StudioLayout, panel: 'left' | 'middle' | 'right'): StudioLayout {
  const key = `${panel}Collapsed` as keyof StudioLayout
  return { ...layout, [key]: !layout[key] }
}

export function resetStudioLayout(): StudioLayout {
  return { ...DEFAULT_STUDIO_LAYOUT }
}
