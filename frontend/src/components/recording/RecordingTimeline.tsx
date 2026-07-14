import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle, ChevronDown, ChevronUp, MessageSquare, Trash2,
} from 'lucide-react'
import type { RecordedStep } from '../../recording/types'

const ROW_HEIGHT = 88
const OVERSCAN = 6

interface Props {
  steps: RecordedStep[]
  selectedId?: string | null
  onSelect?: (stepId: string) => void
  onDelete: (stepId: string) => void
  onToggle: (stepId: string, enabled: boolean) => void
  onMoveUp?: (stepId: string) => void
  onMoveDown?: (stepId: string) => void
  onComment?: (stepId: string, comment: string) => void
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

function locatorLabel(step: RecordedStep): string {
  const loc = step.locator as { locator_type?: string; display_name?: string } | null | undefined
  if (!loc) return '—'
  return loc.display_name || loc.locator_type?.replace(/_/g, ' ') || '—'
}

function targetLabel(step: RecordedStep): string {
  const el = step.element as {
    resource_id?: string
    text?: string
    content_desc?: string
    class_name?: string
  } | null | undefined
  if (el?.text) return el.text
  if (el?.content_desc) return el.content_desc
  if (el?.resource_id) return el.resource_id.split('/').pop() || el.resource_id
  return el?.class_name?.split('.').pop() || 'element'
}

function StepCard({
  step,
  selected,
  onSelect,
  onDelete,
  onToggle,
  onMoveUp,
  onMoveDown,
  onComment,
  style,
}: {
  step: RecordedStep
  selected: boolean
  onSelect?: (id: string) => void
  onDelete: (id: string) => void
  onToggle: (id: string, enabled: boolean) => void
  onMoveUp?: (id: string) => void
  onMoveDown?: (id: string) => void
  onComment?: (id: string, comment: string) => void
  style?: React.CSSProperties
}) {
  const [editingComment, setEditingComment] = useState(false)
  const comment = (step as RecordedStep & { comment?: string }).comment || ''

  return (
    <div
      className={`timeline-step studio-action-card ${step.enabled ? '' : 'disabled'} ${step.needs_review ? 'review' : ''} ${selected ? 'selected' : ''}`}
      style={style}
      onClick={() => onSelect?.(step.id)}
      onKeyDown={(e) => { if (e.key === 'Enter') onSelect?.(step.id) }}
      role="button"
      tabIndex={0}
    >
      <div className="studio-action-header">
        <span className="step-num">Step {step.step_number}</span>
        <span className="step-action">{step.action_type.replace(/_/g, ' ')}</span>
        {step.execution_status && (
          <span className={`step-status ${step.execution_status}`}>{step.execution_status}</span>
        )}
        <div className="studio-action-tools" onClick={(e) => e.stopPropagation()}>
          <button type="button" className="btn-icon copy-btn" title="Move up" onClick={() => onMoveUp?.(step.id)}>
            <ChevronUp size={12} />
          </button>
          <button type="button" className="btn-icon copy-btn" title="Move down" onClick={() => onMoveDown?.(step.id)}>
            <ChevronDown size={12} />
          </button>
          <button
            type="button"
            className="btn-icon copy-btn"
            title="Comment"
            onClick={() => setEditingComment((v) => !v)}
          >
            <MessageSquare size={12} />
          </button>
          <label className="step-toggle" title="Enable/disable">
            <input
              type="checkbox"
              checked={step.enabled}
              onChange={(e) => onToggle(step.id, e.target.checked)}
            />
          </label>
          <button type="button" className="btn-icon copy-btn" title="Delete" onClick={() => onDelete(step.id)}>
            <Trash2 size={12} />
          </button>
        </div>
      </div>
      <div className="studio-action-body">
        <code className="step-locator">{locatorLabel(step)}</code>
        <span className="step-element">{targetLabel(step)}</span>
        <span className="step-time">{formatTime(step.timestamp)}</span>
      </div>
      {step.needs_review && (
        <div className="step-review">
          <AlertTriangle size={12} /> {step.review_reason || 'Review suggested'}
        </div>
      )}
      {(editingComment || comment) && (
        <div className="studio-action-comment" onClick={(e) => e.stopPropagation()}>
          <input
            type="text"
            placeholder="Add comment…"
            defaultValue={comment}
            onBlur={(e) => {
              onComment?.(step.id, e.target.value)
              setEditingComment(false)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                onComment?.(step.id, (e.target as HTMLInputElement).value)
                setEditingComment(false)
              }
            }}
          />
        </div>
      )}
    </div>
  )
}

export default function RecordingTimeline({
  steps,
  selectedId,
  onSelect,
  onDelete,
  onToggle,
  onMoveUp,
  onMoveDown,
  onComment,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportH, setViewportH] = useState(400)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setViewportH(el.clientHeight))
    ro.observe(el)
    setViewportH(el.clientHeight)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    if (!selectedId || !scrollRef.current) return
    const idx = steps.findIndex((s) => s.id === selectedId)
    if (idx < 0) return
    const top = idx * ROW_HEIGHT
    const bottom = top + ROW_HEIGHT
    const { scrollTop: st, clientHeight } = scrollRef.current
    if (top < st || bottom > st + clientHeight) {
      scrollRef.current.scrollTop = top - ROW_HEIGHT
    }
  }, [selectedId, steps])

  const { startIdx, endIdx, offsetY, totalHeight } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN)
    const visible = Math.ceil(viewportH / ROW_HEIGHT) + OVERSCAN * 2
    const end = Math.min(steps.length, start + visible)
    return {
      startIdx: start,
      endIdx: end,
      offsetY: start * ROW_HEIGHT,
      totalHeight: steps.length * ROW_HEIGHT,
    }
  }, [scrollTop, viewportH, steps.length])

  const visibleSteps = useMemo(
    () => steps.slice(startIdx, endIdx),
    [steps, startIdx, endIdx],
  )

  const onScroll = useCallback(() => {
    if (scrollRef.current) setScrollTop(scrollRef.current.scrollTop)
  }, [])

  if (!steps.length) {
    return (
      <div className="recording-timeline studio-actions empty">
        <p>No actions recorded yet.</p>
        <p className="hint">Start recording, tap an element on the screenshot, then use quick actions below.</p>
      </div>
    )
  }

  return (
    <div
      ref={scrollRef}
      className="recording-timeline studio-actions virtual"
      onScroll={onScroll}
    >
      <div className="virtual-scroll-spacer" style={{ height: totalHeight }}>
        <div className="virtual-scroll-window" style={{ transform: `translateY(${offsetY}px)` }}>
          {visibleSteps.map((step) => (
            <StepCard
              key={step.id}
              step={step}
              selected={selectedId === step.id}
              onSelect={onSelect}
              onDelete={onDelete}
              onToggle={onToggle}
              onMoveUp={onMoveUp}
              onMoveDown={onMoveDown}
              onComment={onComment}
              style={{ height: ROW_HEIGHT - 8 }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
