import { LANGUAGE_PROFILES } from './types'

const EXT: Record<string, string> = {
  python_uiautomator2: 'py',
  python_appium: 'py',
  java_uiautomator: 'java',
  java_appium: 'java',
  javascript_wdio: 'js',
  javascript_appium: 'js',
  adb_shell: 'sh',
}

const BASENAME: Record<string, string> = {
  python_uiautomator2: 'test_recording',
  python_appium: 'test_recording',
  java_uiautomator: 'RecordingTest',
  java_appium: 'RecordingTest',
  javascript_wdio: 'recording.spec',
  javascript_appium: 'recording.spec',
  adb_shell: 'recording',
}

export function recordingFilename(languageProfile: string): string {
  const ext = EXT[languageProfile] ?? 'txt'
  const base = BASENAME[languageProfile] ?? 'recording'
  return `${base}.${ext}`
}

export function profileLabel(languageProfile: string): string {
  return LANGUAGE_PROFILES.find((p) => p.id === languageProfile)?.label ?? languageProfile
}

export function countScriptLines(script: string): number {
  return script ? script.split('\n').length : 0
}

export function downloadTextFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.left = '-9999px'
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  document.body.removeChild(ta)
}
