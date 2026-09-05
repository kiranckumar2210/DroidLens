/** Client-side locator export — current element or saved repository. */

import type { ElementInspectionResult, LocatorCandidate } from '../types'

export type ExportFormat = 'json' | 'csv' | 'markdown'

export interface RepositoryElement {
  project: string
  feature: string
  screen: string
  platform: string
  element_name: string
  class_name: string
  bounds: string
  captured_at: string | null
  primary_locator: Record<string, unknown> | null
  locators: Array<Record<string, unknown>>
}

function escapeCsv(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}

export function inspectionToExportPayload(
  inspection: ElementInspectionResult,
  meta?: { screenName?: string; packageName?: string; elementName?: string },
) {
  return {
    format: 'droidlens-element-locators',
    formatVersion: 1,
    exportedAt: new Date().toISOString(),
    screenName: meta?.screenName ?? null,
    packageName: meta?.packageName ?? null,
    elementName: meta?.elementName ?? inspection.element.resource_id ?? inspection.element.id,
    element: inspection.element,
    analysis: inspection.analysis ?? null,
    locators: inspection.locators,
    primary: inspection.locators.find((l) => l.recommended) ?? inspection.locators[0] ?? null,
  }
}

export function locatorsToJson(
  inspection: ElementInspectionResult,
  meta?: { screenName?: string; packageName?: string; elementName?: string },
): string {
  return JSON.stringify(inspectionToExportPayload(inspection, meta), null, 2)
}

export function locatorsToCsv(locators: LocatorCandidate[], meta?: { elementName?: string; screenName?: string }): string {
  const header = ['element', 'screen', 'display_name', 'locator_type', 'value', 'overall', 'recommended', 'reason']
  const rows = locators.map((loc) => [
    meta?.elementName ?? '',
    meta?.screenName ?? '',
    loc.display_name,
    loc.locator_type,
    loc.value,
    `${Math.round(loc.scores.overall * 100)}%`,
    loc.recommended ? 'yes' : '',
    loc.reason,
  ])
  return [header, ...rows].map((row) => row.map((c) => escapeCsv(String(c))).join(',')).join('\n')
}

export function locatorsToMarkdown(
  inspection: ElementInspectionResult,
  meta?: { screenName?: string; packageName?: string; elementName?: string },
): string {
  const el = inspection.element
  const name = meta?.elementName ?? el.text ?? el.resource_id ?? el.id
  const lines = [
    `# ${name}`,
    '',
    meta?.screenName ? `**Screen:** ${meta.screenName}` : '',
    meta?.packageName ? `**Package:** ${meta.packageName}` : '',
    '',
    '| Locator | Type | Score | Recommended |',
    '| --- | --- | --- | --- |',
  ].filter(Boolean)
  for (const loc of inspection.locators) {
    const val = loc.value.replace(/\|/g, '\\|').slice(0, 120)
    lines.push(
      `| ${loc.display_name} | ${loc.locator_type} | ${Math.round(loc.scores.overall * 100)}% | ${loc.recommended ? '✓' : ''} |`,
    )
    lines.push(`| \`${val}\` | | | |`)
  }
  lines.push('', '## Details', '')
  for (const loc of inspection.locators) {
    lines.push(`### ${loc.display_name}`)
    lines.push('')
    lines.push('```')
    lines.push(loc.value)
    lines.push('```')
    lines.push('')
    lines.push(`> ${loc.reason}`)
    lines.push('')
  }
  return lines.join('\n')
}

export function repositoryToCsv(elements: RepositoryElement[]): string {
  const header = [
    'project', 'feature', 'screen', 'platform', 'element_name', 'class_name',
    'locator_type', 'locator_value', 'overall_score', 'is_primary', 'recommended', 'reason',
  ]
  const rows: string[][] = [header]
  for (const row of elements) {
    for (const loc of row.locators) {
      rows.push([
        row.project,
        row.feature,
        row.screen,
        row.platform,
        row.element_name,
        row.class_name,
        String(loc.locator_type ?? ''),
        String(loc.value ?? ''),
        `${Math.round(Number(loc.overall ?? 0) * 100)}%`,
        loc.is_primary ? 'yes' : '',
        loc.recommended ? 'yes' : '',
        String(loc.reason ?? ''),
      ])
    }
  }
  return rows.map((row) => row.map((c) => escapeCsv(c)).join(',')).join('\n')
}

export function repositoryToMarkdown(elements: RepositoryElement[]): string {
  const lines = [
    '# DroidLens Locator Repository',
    '',
    `**Elements:** ${elements.length}`,
    '',
    '| Project | Feature | Screen | Element | Primary | Score |',
    '| --- | --- | --- | --- | --- | --- |',
  ]
  for (const row of elements) {
    const primary = row.primary_locator
    const val = primary ? String(primary.value ?? '').replace(/\|/g, '\\|') : '—'
    const score = primary ? `${Math.round(Number(primary.overall ?? 0) * 100)}%` : '—'
    lines.push(`| ${row.project} | ${row.feature} | ${row.screen} | ${row.element_name} | \`${val.slice(0, 60)}\` | ${score} |`)
  }
  return lines.join('\n')
}

export function downloadText(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function formatForExport(
  format: ExportFormat,
  inspection: ElementInspectionResult | null,
  repository: RepositoryElement[] | null,
  meta?: { screenName?: string; packageName?: string; elementName?: string },
): { content: string; filename: string; mime: string } | null {
  if (inspection) {
    const base = meta?.elementName ?? 'element'
    if (format === 'json') {
      return { content: locatorsToJson(inspection, meta), filename: `${base}-locators.json`, mime: 'application/json' }
    }
    if (format === 'csv') {
      return {
        content: locatorsToCsv(inspection.locators, meta),
        filename: `${base}-locators.csv`,
        mime: 'text/csv',
      }
    }
    return {
      content: locatorsToMarkdown(inspection, meta),
      filename: `${base}-locators.md`,
      mime: 'text/markdown',
    }
  }
  if (repository?.length) {
    if (format === 'json') {
      return {
        content: JSON.stringify({ format: 'droidlens-locator-repository', formatVersion: 1, elements: repository }, null, 2),
        filename: 'locator-repository.json',
        mime: 'application/json',
      }
    }
    if (format === 'csv') {
      return { content: repositoryToCsv(repository), filename: 'locator-repository.csv', mime: 'text/csv' }
    }
    return { content: repositoryToMarkdown(repository), filename: 'locator-repository.md', mime: 'text/markdown' }
  }
  return null
}
