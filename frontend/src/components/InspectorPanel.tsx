import { useCallback, useEffect, useRef, type Dispatch, type SetStateAction } from 'react'
import { AlertCircle, CheckCircle, ChevronDown, Lock } from 'lucide-react'
import { api } from '../api/client'
import type { CustomLocatorResult, ElementInspectionResult, LocatorCandidate } from '../types'
import MonacoLocatorEditor, { type LocatorEditorLanguage } from './MonacoLocatorEditor'
import TextViewPanel from './TextViewPanel'
import LocatorEnginePanel from './LocatorEnginePanel'

export type InspectorSection = 'locators' | 'text' | 'builder'

export type BuilderState = {
  locatorType: LocatorEditorLanguage
  xpathText: string
  uiSelectorText: string
  cssText: string
  attr: string
  op: string
  value: string
  axis: string
  anchorAttr: string
  anchorOp: string
  anchorValue: string
  relationship: string
  validation: {
    valid: boolean
    match_count: number
    warning?: string | null
    error?: string | null
  } | null
  ruleResult: CustomLocatorResult | null
}

interface Props {
  inspection: ElementInspectionResult | null
  selectedLocator?: LocatorCandidate | null
  onSelectLocator: (loc: LocatorCandidate) => void
  onPreviewLocator?: (loc: LocatorCandidate) => void
  deviceId: string | null
  expandedSection: InspectorSection
  onSectionChange: (section: InspectorSection) => void
  builderState: BuilderState
  onBuilderStateChange: Dispatch<SetStateAction<BuilderState>>
  onHighlightMatches: (ids: string[]) => void
  theme: 'dark' | 'light'
  premiumLocked?: boolean
  elementName?: string
  packageName?: string
}

const DEFAULT_BUILDER: BuilderState = {
  locatorType: 'xpath',
  xpathText: '',
  uiSelectorText: '',
  cssText: '',
  attr: 'resource-id',
  op: 'equals',
  value: '',
  axis: '',
  anchorAttr: 'text',
  anchorOp: 'equals',
  anchorValue: '',
  relationship: '',
  validation: null,
  ruleResult: null,
}

export { DEFAULT_BUILDER }

function editorValue(state: BuilderState): string {
  if (state.locatorType === 'xpath') return state.xpathText
  if (state.locatorType === 'uiselector') return state.uiSelectorText
  return state.cssText
}

function updateEditorValue(state: BuilderState, value: string): BuilderState {
  if (state.locatorType === 'xpath') return { ...state, xpathText: value }
  if (state.locatorType === 'uiselector') return { ...state, uiSelectorText: value }
  return { ...state, cssText: value }
}

export default function InspectorPanel({
  inspection,
  selectedLocator,
  onSelectLocator,
  onPreviewLocator,
  deviceId,
  expandedSection,
  onSectionChange,
  builderState,
  onBuilderStateChange,
  onHighlightMatches,
  theme,
  premiumLocked = false,
  elementName,
  packageName,
}: Props) {
  const debounceRef = useRef<number | null>(null)
  const scrollPosRef = useRef(0)

  const validateRaw = useCallback(async (type: string, expr: string) => {
    if (!deviceId || !expr.trim()) {
      onBuilderStateChange((prev) => ({ ...prev, validation: null }))
      onHighlightMatches([])
      return
    }
    if (type === 'css') {
      onBuilderStateChange((prev) => ({
        ...prev,
        validation: { valid: false, match_count: 0, warning: 'CSS locators are reserved for future support' },
      }))
      onHighlightMatches([])
      return
    }
    try {
      const r = await api.validateRawLocator(deviceId, type, expr)
      onBuilderStateChange((prev) => ({ ...prev, validation: r }))
      onHighlightMatches(r.matched_ids || [])
    } catch {
      onBuilderStateChange((prev) => ({
        ...prev,
        validation: { valid: false, match_count: 0, error: 'Validation failed' },
      }))
    }
  }, [deviceId, onBuilderStateChange, onHighlightMatches])

  useEffect(() => {
    if (expandedSection !== 'builder') return
    const expr = editorValue(builderState)
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(
      () => validateRaw(builderState.locatorType, expr),
      300,
    )
    return () => { if (debounceRef.current) window.clearTimeout(debounceRef.current) }
  }, [
    builderState.xpathText,
    builderState.uiSelectorText,
    builderState.cssText,
    builderState.locatorType,
    expandedSection,
    validateRaw,
  ])

  const buildFromRules = async () => {
    if (!deviceId || !builderState.value.trim()) return
    const options: Record<string, string> = {}
    if (builderState.axis) options.axis = builderState.axis
    if (builderState.relationship) options.relationship = builderState.relationship
    if (builderState.anchorValue.trim()) {
      options.anchor_attribute = builderState.anchorAttr
      options.anchor_operator = builderState.anchorOp
      options.anchor_value = builderState.anchorValue.trim()
    }
    const r = await api.customLocator(deviceId, [
      { attribute: builderState.attr, operator: builderState.op, value: builderState.value.trim() },
    ], options)
    onBuilderStateChange((prev) => ({
      ...prev,
      ruleResult: r,
      xpathText: r.xpath,
      uiSelectorText: r.uiautomator2,
      validation: {
        valid: r.match_count > 0,
        match_count: r.match_count,
        warning: r.match_count > 1 ? 'Multiple matches' : null,
      },
    }))
    onHighlightMatches(r.matched_elements?.map((e) => e.id) || [])
  }

  const prefillFromElement = () => {
    if (!inspection) return
    const el = inspection.element
    onBuilderStateChange((prev) => ({
      ...prev,
      value: el.text || el.resource_id || el.content_desc || '',
      attr: el.resource_id ? 'resource-id' : el.text ? 'text' : 'content-desc',
      anchorValue: inspection.parent?.text || inspection.parent?.resource_id || '',
      anchorAttr: inspection.parent?.text ? 'text' : 'resource-id',
    }))
  }

  const handleSectionToggle = (section: InspectorSection) => {
    if (premiumLocked && section === 'builder') return
    if (expandedSection === section) return
    const inner = document.querySelector('.expand-tile.expanded .expand-tile-inner')
    if (inner) scrollPosRef.current = inner.scrollTop
    onSectionChange(section)
  }

  return (
    <div className="panel inspector-accordion">
      <ExpandTile
        title="Smart Locators"
        expanded={expandedSection === 'locators'}
        onToggle={() => handleSectionToggle('locators')}
      >
        <LocatorEnginePanel
          inspection={inspection}
          selectedLocator={selectedLocator}
          onSelectLocator={onSelectLocator}
          onPreviewLocator={onPreviewLocator}
          onHighlightMatches={onHighlightMatches}
          deviceId={deviceId}
          theme={theme}
          elementName={elementName}
          packageName={packageName}
        />
      </ExpandTile>

      <ExpandTile
        title="Text View"
        expanded={expandedSection === 'text'}
        onToggle={() => handleSectionToggle('text')}
      >
        <TextViewPanel
          inspection={inspection}
          selectedLocator={selectedLocator}
          onSelectLocator={onSelectLocator}
          onPreviewLocator={onPreviewLocator}
        />
      </ExpandTile>

      <ExpandTile
        title="Custom Locator Builder"
        expanded={expandedSection === 'builder'}
        onToggle={() => handleSectionToggle('builder')}
        locked={premiumLocked}
        lockHint="Requires account & active license"
      >
        {premiumLocked ? (
          <p className="locked-hint">Sign in or purchase a license to use the Custom Locator Builder.</p>
        ) : (
        <div className="builder-editor">
          <div className="builder-tabs">
            {(['xpath', 'uiselector', 'css'] as LocatorEditorLanguage[]).map((t) => (
              <button
                key={t}
                className={builderState.locatorType === t ? 'active' : ''}
                onClick={() => onBuilderStateChange((prev) => ({ ...prev, locatorType: t }))}
              >
                {t === 'xpath' ? 'XPath / Relative XPath' : t === 'uiselector' ? 'UiSelector' : 'CSS (future)'}
              </button>
            ))}
          </div>

          <label className="field-label">Expression Editor</label>
          <MonacoLocatorEditor
            value={editorValue(builderState)}
            onChange={(v) => onBuilderStateChange((prev) => updateEditorValue(prev, v))}
            language={builderState.locatorType}
            theme={theme}
            height={200}
            hasError={builderState.validation?.valid === false}
          />

          {builderState.validation && (
            <div className={`validation-banner ${builderState.validation.valid ? 'ok' : 'warn'}`}>
              {builderState.validation.valid ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
              <span>
                {builderState.validation.match_count} match(es)
                {builderState.validation.warning && ` — ${builderState.validation.warning}`}
                {builderState.validation.error && ` — ${builderState.validation.error}`}
                {builderState.validation.match_count === 0 && !builderState.validation.error && ' — No elements match'}
              </span>
            </div>
          )}

          <label className="field-label">Visual Rule Builder</label>
          <button type="button" className="link-btn" onClick={prefillFromElement} disabled={!inspection}>
            Prefill from selected element
          </button>
          <div className="builder-row">
            <select value={builderState.attr} onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, attr: e.target.value }))}>
              {['resource-id', 'text', 'class', 'content-desc', 'package'].map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
            <select value={builderState.op} onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, op: e.target.value }))}>
              {['equals', 'contains', 'starts_with', 'ends_with', 'regex'].map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          </div>
          <input
            className="full-width"
            placeholder="Target value..."
            value={builderState.value}
            onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, value: e.target.value }))}
          />

          <label className="field-label">Relative Locator Builder</label>
          <p className="field-hint">Identify element by relationship to a nearby anchor (e.g. button next to &quot;Username&quot;)</p>
          <div className="builder-row">
            <select
              value={builderState.relationship}
              onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, relationship: e.target.value }))}
            >
              {[
                ['', 'No relationship'],
                ['child_of', 'Child of anchor'],
                ['inside', 'Inside / descendant of anchor'],
                ['sibling_after', 'Following sibling of anchor'],
                ['sibling_before', 'Preceding sibling of anchor'],
                ['below', 'Below anchor (sibling)'],
                ['above', 'Above anchor (sibling)'],
              ].map(([v, l]) => (
                <option key={v || 'none'} value={v}>{l}</option>
              ))}
            </select>
          </div>
          {builderState.relationship && (
            <>
              <div className="builder-row">
                <select
                  value={builderState.anchorAttr}
                  onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, anchorAttr: e.target.value }))}
                >
                  {['text', 'resource-id', 'content-desc', 'class'].map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
                <select
                  value={builderState.anchorOp}
                  onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, anchorOp: e.target.value }))}
                >
                  {['equals', 'contains', 'starts_with'].map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
              <input
                className="full-width"
                placeholder='Anchor value (e.g. "Settings", "Username")...'
                value={builderState.anchorValue}
                onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, anchorValue: e.target.value }))}
              />
            </>
          )}

          <select
            className="full-width"
            value={builderState.axis}
            onChange={(e) => onBuilderStateChange((prev) => ({ ...prev, axis: e.target.value }))}
          >
            {['', 'parent', 'child', 'sibling', 'ancestor', 'descendant'].map((a) => (
              <option key={a || 'none'} value={a}>{a ? `XPath axis: ${a}` : 'No XPath axis'}</option>
            ))}
          </select>
          <button onClick={buildFromRules} disabled={!deviceId || !builderState.value.trim()}>
            Build & Validate
          </button>

          {builderState.ruleResult && (
            <div className="builder-result">
              <div className="mono result-block">{builderState.ruleResult.uiautomator2}</div>
              <div className="mono result-block">{builderState.ruleResult.xpath}</div>
            </div>
          )}
        </div>
        )}
      </ExpandTile>
    </div>
  )
}

function ExpandTile({
  title, expanded, onToggle, children, locked, lockHint,
}: {
  title: string
  expanded: boolean
  onToggle: () => void
  children: React.ReactNode
  locked?: boolean
  lockHint?: string
}) {
  return (
    <div className={`expand-tile ${expanded ? 'expanded' : 'collapsed'} ${locked ? 'locked' : ''}`}>
      <button
        className="expand-tile-header"
        onClick={onToggle}
        aria-expanded={expanded}
        type="button"
        title={locked ? lockHint : undefined}
      >
        <ChevronDown size={16} className={`chevron ${expanded ? 'open' : ''}`} />
        <span>{title}</span>
        {locked && <Lock size={12} className="expand-tile-lock" />}
      </button>
      <div className="expand-tile-body" aria-hidden={!expanded}>
        <div className="expand-tile-inner">{children}</div>
      </div>
    </div>
  )
}
