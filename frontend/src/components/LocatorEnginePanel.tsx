import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, Check, CheckCircle, ChevronDown, ChevronRight, Copy,
  GitCompare, Lightbulb, Search, Star,
} from 'lucide-react'
import { api } from '../api/client'
import type {
  ElementInspectionResult,
  LocatorCandidate,
  LocatorComparisonResult,
  LocatorGroup,
} from '../types'
import MonacoLocatorEditor, { type LocatorEditorLanguage } from './MonacoLocatorEditor'

type EngineTab = 'summary' | 'code' | 'reliability' | 'compare'

const CODE_PROFILES: { id: string; label: string; monaco: LocatorEditorLanguage }[] = [
  { id: 'java_appium', label: 'Java', monaco: 'java' },
  { id: 'python_appium', label: 'Python', monaco: 'python' },
  { id: 'javascript_appium', label: 'JavaScript', monaco: 'javascript' },
  { id: 'csharp_appium', label: 'C#', monaco: 'csharp' },
  { id: 'ruby_appium', label: 'Ruby', monaco: 'ruby' },
  { id: 'kotlin_appium', label: 'Kotlin', monaco: 'kotlin' },
]

interface Props {
  inspection: ElementInspectionResult | null
  selectedLocator?: LocatorCandidate | null
  onSelectLocator: (loc: LocatorCandidate) => void
  onPreviewLocator?: (loc: LocatorCandidate) => void
  onHighlightMatches: (ids: string[]) => void
  deviceId: string | null
  theme: 'dark' | 'light'
  elementName?: string
  packageName?: string
}

function badgeClass(badge?: string | null) {
  if (badge === 'recommended') return 'recommended'
  if (badge === 'good') return 'good'
  if (badge === 'avoid') return 'avoid'
  return 'neutral'
}

function stars(rating?: number | null) {
  const n = Math.round(rating ?? 3)
  return Array.from({ length: 5 }, (_, i) => (
    <Star key={i} size={11} className={i < n ? 'star-filled' : 'star-empty'} />
  ))
}

function LocatorRow({
  loc,
  active,
  onSelect,
  onValidate,
  onCopy,
  validating,
  validation,
  expanded,
  onToggle,
}: {
  loc: LocatorCandidate
  active: boolean
  onSelect: () => void
  onValidate: () => void
  onCopy: () => void
  validating: boolean
  validation?: { match_count: number; execution_ms?: number; warning?: string | null } | null
  expanded: boolean
  onToggle: () => void
}) {
  const matchCount = validation?.match_count ?? loc.match_count ?? 1
  return (
    <div className={`locator-card engine-locator-row ${active ? 'active' : ''}`}>
      <div className="locator-header" onClick={onSelect} role="button" tabIndex={0}>
        <button type="button" className="expand-btn" onClick={(e) => { e.stopPropagation(); onToggle() }}>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <span className="locator-name">
          {loc.recommended && <Star size={12} className="star-icon" />}
          {loc.display_name}
        </span>
        <div className="locator-badges">
          <span className="star-rating">{stars(loc.star_rating)}</span>
          <span className={`badge ${badgeClass(loc.badge)}`}>{loc.badge || 'fair'}</span>
          {matchCount > 1 && <span className="badge warn">{matchCount} matches</span>}
        </div>
      </div>
      {expanded && (
        <>
          <div className="locator-value mono">{loc.value}</div>
          <div className="locator-meta">
            <span className="locator-reason">{loc.reason}</span>
            <div className="locator-meta-tags">
              {loc.performance_rating && <span className="meta-tag">{loc.performance_rating}</span>}
              {loc.robustness && <span className={`meta-tag robustness-${loc.robustness}`}>{loc.robustness}</span>}
              {validation?.execution_ms != null && (
                <span className="meta-tag">{validation.execution_ms}ms</span>
              )}
            </div>
          </div>
          {validation?.warning && (
            <div className="validation-banner warn compact">
              <AlertCircle size={12} />
              <span>{validation.warning}</span>
            </div>
          )}
          <div className="locator-actions">
            <button type="button" className="copy-btn" onClick={onCopy}><Copy size={12} /> Copy</button>
            <button type="button" className="copy-btn" onClick={onValidate} disabled={validating}>
              {validating ? '…' : 'Validate'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default function LocatorEnginePanel({
  inspection,
  selectedLocator,
  onSelectLocator,
  onPreviewLocator,
  onHighlightMatches,
  deviceId,
  theme,
  elementName = 'element',
  packageName = 'com.example.app',
}: Props) {
  const [tab, setTab] = useState<EngineTab>('summary')
  const [codeProfile, setCodeProfile] = useState('python_appium')
  const [generatedCode, setGeneratedCode] = useState('')
  const [codeLoading, setCodeLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({})
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({})
  const [validations, setValidations] = useState<Record<string, { match_count: number; execution_ms?: number; warning?: string | null }>>({})
  const [validatingKey, setValidatingKey] = useState<string | null>(null)
  const [compareA, setCompareA] = useState<LocatorCandidate | null>(null)
  const [compareB, setCompareB] = useState<LocatorCandidate | null>(null)
  const [compareResult, setCompareResult] = useState<LocatorComparisonResult | null>(null)
  const [copied, setCopied] = useState(false)

  const groups: LocatorGroup[] = useMemo(() => {
    if (inspection?.grouped_locators?.length) return inspection.grouped_locators
    if (!inspection?.locators.length) return []
    return [{ category: 'all', label: 'All Locators', locators: inspection.locators }]
  }, [inspection])

  const suggestions = inspection?.suggestions ?? []
  const analysis = inspection?.analysis

  useEffect(() => {
    const init: Record<string, boolean> = {}
    groups.forEach((g) => { init[g.category] = true })
    setExpandedCats(init)
  }, [groups])

  useEffect(() => {
    if (!selectedLocator || tab !== 'code') return
    let cancelled = false
    setCodeLoading(true)
    api.generateCode(selectedLocator, codeProfile, 'click', elementName, packageName)
      .then((r) => { if (!cancelled) setGeneratedCode(r.code) })
      .catch(() => { if (!cancelled) setGeneratedCode('// Code generation failed') })
      .finally(() => { if (!cancelled) setCodeLoading(false) })
    return () => { cancelled = true }
  }, [selectedLocator, codeProfile, tab, elementName, packageName])

  const validateLocator = useCallback(async (loc: LocatorCandidate) => {
    if (!deviceId) return
    const key = `${loc.locator_type}:${loc.value}`
    setValidatingKey(key)
    try {
      const r = await api.previewLocator(deviceId, loc.locator_type, loc.value)
      setValidations((prev) => ({ ...prev, [key]: r }))
      onHighlightMatches(r.matched_ids || [])
    } finally {
      setValidatingKey(null)
    }
  }, [deviceId, onHighlightMatches])

  const runCompare = async () => {
    if (!deviceId || !compareA || !compareB) return
    const r = await api.compareLocators(deviceId, compareA, compareB)
    setCompareResult(r)
  }

  const filteredGroups = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return groups
    return groups
      .map((g) => ({
        ...g,
        locators: g.locators.filter(
          (l) => l.display_name.toLowerCase().includes(q)
            || l.value.toLowerCase().includes(q)
            || (l.category || '').includes(q),
        ),
      }))
      .filter((g) => g.locators.length > 0)
  }, [groups, search])

  if (!inspection) {
    return <div className="empty-state">Click an element to generate locators</div>
  }

  const copyText = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="locator-engine-panel">
      <div className="engine-tabs">
        {([
          ['summary', 'Locator Summary'],
          ['code', 'Generated Code'],
          ['reliability', 'Reliability'],
          ['compare', 'Compare'],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? 'active' : ''}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'summary' && (
        <div className="engine-tab-content">
          <div className="engine-search">
            <Search size={14} />
            <input
              placeholder="Filter locators…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {filteredGroups.map((group) => (
            <section key={group.category} className="locator-group-section">
              <button
                type="button"
                className="locator-group-header"
                onClick={() => setExpandedCats((p) => ({ ...p, [group.category]: !p[group.category] }))}
              >
                <ChevronDown size={14} className={expandedCats[group.category] ? 'open' : ''} />
                <span>{group.label}</span>
                <span className="group-count">{group.locators.length}</span>
              </button>
              {expandedCats[group.category] && group.locators.map((loc) => {
                const key = `${loc.locator_type}:${loc.value}`
                return (
                  <LocatorRow
                    key={key}
                    loc={loc}
                    active={selectedLocator?.value === loc.value}
                    onSelect={() => {
                      onSelectLocator(loc)
                      onPreviewLocator?.(loc)
                    }}
                    onValidate={() => validateLocator(loc)}
                    onCopy={() => copyText(loc.value)}
                    validating={validatingKey === key}
                    validation={validations[key]}
                    expanded={expandedRows[key] ?? loc.recommended}
                    onToggle={() => setExpandedRows((p) => ({ ...p, [key]: !p[key] }))}
                  />
                )
              })}
            </section>
          ))}
        </div>
      )}

      {tab === 'code' && (
        <div className="engine-tab-content">
          {!selectedLocator ? (
            <p className="field-hint">Select a locator from Summary to generate code.</p>
          ) : (
            <>
              <div className="code-lang-tabs">
                {CODE_PROFILES.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={codeProfile === p.id ? 'active' : ''}
                    onClick={() => setCodeProfile(p.id)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <div className="code-editor-toolbar">
                <span className="field-hint">{selectedLocator.display_name}</span>
                <button type="button" className="copy-btn" onClick={() => copyText(generatedCode)}>
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  Copy
                </button>
              </div>
              {codeLoading ? (
                <p className="field-hint">Generating…</p>
              ) : (
                <MonacoLocatorEditor
                  value={generatedCode}
                  onChange={setGeneratedCode}
                  language={CODE_PROFILES.find((p) => p.id === codeProfile)?.monaco ?? 'python'}
                  theme={theme}
                  height={320}
                  readOnly
                />
              )}
            </>
          )}
        </div>
      )}

      {tab === 'reliability' && (
        <div className="engine-tab-content">
          {analysis && (
            <section className="prop-section analysis-grid">
              <h4>Element Analysis</h4>
              <div className="analysis-stats">
                <span>Depth: {analysis.hierarchy_level}</span>
                <span>Siblings: {analysis.sibling_count}</span>
                <span>Children: {analysis.child_count}</span>
                {analysis.is_in_recyclerview && <span className="badge warn">RecyclerView</span>}
                {analysis.has_dynamic_text && <span className="badge warn">Dynamic text</span>}
              </div>
            </section>
          )}
          {suggestions.length > 0 && (
            <section className="prop-section">
              <h4><Lightbulb size={12} /> Smart Suggestions</h4>
              {suggestions.map((s, i) => (
                <div key={i} className={`suggestion-card ${s.severity}`}>
                  <strong>{s.message}</strong>
                  {s.hint && <p>{s.hint}</p>}
                </div>
              ))}
            </section>
          )}
          <section className="prop-section">
            <h4>Score Breakdown</h4>
            {(selectedLocator ? [selectedLocator] : inspection.locators.slice(0, 5)).map((loc, i) => (
              <div key={i} className="reliability-row">
                <span>{loc.display_name}</span>
                <div className="reliability-scores">
                  <span title="Stability">S {Math.round(loc.scores.stability * 100)}%</span>
                  <span title="Uniqueness">U {Math.round(loc.scores.uniqueness * 100)}%</span>
                  <span title="Maintainability">M {Math.round(loc.scores.maintainability * 100)}%</span>
                  <span className="overall">{Math.round(loc.scores.overall * 100)}%</span>
                </div>
              </div>
            ))}
          </section>
        </div>
      )}

      {tab === 'compare' && (
        <div className="engine-tab-content">
          <p className="field-hint"><GitCompare size={12} /> Pick two locators to compare side-by-side.</p>
          <div className="compare-pickers">
            <select
              value={compareA?.value ?? ''}
              onChange={(e) => setCompareA(inspection.locators.find((l) => l.value === e.target.value) ?? null)}
            >
              <option value="">Locator A…</option>
              {inspection.locators.map((l) => (
                <option key={`a-${l.value}`} value={l.value}>{l.display_name}</option>
              ))}
            </select>
            <select
              value={compareB?.value ?? ''}
              onChange={(e) => setCompareB(inspection.locators.find((l) => l.value === e.target.value) ?? null)}
            >
              <option value="">Locator B…</option>
              {inspection.locators.map((l) => (
                <option key={`b-${l.value}`} value={l.value}>{l.display_name}</option>
              ))}
            </select>
            <button type="button" onClick={runCompare} disabled={!compareA || !compareB}>Compare</button>
          </div>
          {compareResult && (
            <div className="compare-result">
              <div className="compare-col">
                <h5>A — {compareResult.locator_a.display_name}</h5>
                <code className="mono">{compareResult.locator_a.value}</code>
                <span>{compareResult.matches_a} matches</span>
              </div>
              <div className="compare-col">
                <h5>B — {compareResult.locator_b.display_name}</h5>
                <code className="mono">{compareResult.locator_b.value}</code>
                <span>{compareResult.matches_b} matches</span>
              </div>
              <div className="compare-summary">
                <CheckCircle size={14} />
                <span>{compareResult.recommendation}</span>
                {compareResult.overlap_count > 0 && (
                  <span className="field-hint">{compareResult.overlap_count} overlapping elements</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
