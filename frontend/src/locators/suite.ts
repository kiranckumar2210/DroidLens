/** DroidLens locator suite format for CI and offline validation. */

export interface LocatorSuiteElement {
  name: string
  locator_type: string
  value: string
  required?: boolean
}

export interface LocatorSuiteScreen {
  name: string
  xml_file?: string
  elements: LocatorSuiteElement[]
}

export interface LocatorSuite {
  format: 'droidlens-locator-suite'
  formatVersion: 1
  project?: string
  screens: LocatorSuiteScreen[]
}

export function buildLocatorSuiteFromInspection(
  screenName: string,
  elements: Array<{ name: string; locator_type: string; value: string }>,
  project?: string,
): LocatorSuite {
  return {
    format: 'droidlens-locator-suite',
    formatVersion: 1,
    project,
    screens: [{ name: screenName, xml_file: `${screenName}.xml`, elements }],
  }
}

export function parseLocatorSuite(raw: unknown): LocatorSuite | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  if (o.format === 'droidlens-locator-suite' && Array.isArray(o.screens)) {
    return o as unknown as LocatorSuite
  }
  return null
}

export function suiteToJson(suite: LocatorSuite): string {
  return JSON.stringify(suite, null, 2)
}

export function downloadSuite(suite: LocatorSuite, filename = 'locators.json'): void {
  const blob = new Blob([suiteToJson(suite)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
