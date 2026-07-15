import { api } from '../api/client'
import { isElectron } from '../api/baseUrl'
import type { InspectionSession } from '../types'
import type { XmlPackagePair } from './xmlPackage'

/** Load one XML+PNG pair into an offline inspection session. */
export async function loadXmlPackagePair(pair: XmlPackagePair): Promise<InspectionSession> {
  if (pair.xml) {
    return api.uploadOffline(pair.xml, pair.screenshot)
  }

  const bridge = window.droidlens ?? window.inspectiq
  if (pair.xmlPath && isElectron() && bridge?.readPackagePaths) {
    const data = await bridge.readPackagePaths(pair.xmlPath, pair.screenshotPath ?? null)
    return api.createOfflineFromContent(data.xml, data.screenshotBase64 ?? undefined)
  }

  throw new Error('Cannot load package — missing file data')
}
