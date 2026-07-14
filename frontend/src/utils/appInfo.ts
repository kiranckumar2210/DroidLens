import { isElectron } from '../api/client'

export const APP_NAME = 'DroidLens'
export const APP_TAGLINE = 'See. Inspect. Automate.'
export const APP_AUTHOR = 'Kiran Kumar C'
export const APP_EMAIL = 'info.kiranc@gmail.com'
export const APP_COPYRIGHT = '© 2026 Kiran Kumar C. All Rights Reserved.'

/** Resolve version from Electron bridge, Vite build define, or fallback. */
export function getAppVersion(): string {
  if (typeof __DROIDLENS_VERSION__ !== 'undefined') return __DROIDLENS_VERSION__
  return window.droidlens?.version || window.inspectiq?.version || '1.0.0'
}

export function getRuntimeLabel(): string {
  if (isElectron()) return 'Desktop (Electron)'
  return 'Web'
}

export function buildVersionClipboardText(opts: {
  version: string
  userLabel: string
  licenseLabel: string
  email?: string
}): string {
  return [
    `${APP_NAME} ${opts.version}`,
    APP_TAGLINE,
    `Runtime: ${getRuntimeLabel()}`,
    `Author: ${APP_AUTHOR}`,
    `Email: ${APP_EMAIL}`,
    `User: ${opts.userLabel}`,
    `License: ${opts.licenseLabel}`,
  ].join('\n')
}
