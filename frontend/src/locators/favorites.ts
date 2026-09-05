/** Persist favorite locators in localStorage — no server required. */

import type { LocatorCandidate } from '../types'

export interface FavoriteLocator {
  id: string
  locator_type: string
  value: string
  display_name: string
  element_label?: string
  screen_label?: string
  package_name?: string
  savedAt: string
}

const STORAGE_KEY = 'droidlens-favorite-locators-v1'
const MAX = 50

export function locatorKey(loc: Pick<LocatorCandidate, 'locator_type' | 'value'>): string {
  return `${loc.locator_type}:${loc.value}`
}

export function loadFavorites(): FavoriteLocator[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as FavoriteLocator[]
  } catch {
    return []
  }
}

export function isFavorite(loc: Pick<LocatorCandidate, 'locator_type' | 'value'>): boolean {
  const key = locatorKey(loc)
  return loadFavorites().some((f) => f.id === key)
}

export function toggleFavorite(
  loc: LocatorCandidate,
  context?: { elementLabel?: string; screenLabel?: string; packageName?: string },
): boolean {
  const key = locatorKey(loc)
  const list = loadFavorites()
  const idx = list.findIndex((f) => f.id === key)
  if (idx >= 0) {
    list.splice(idx, 1)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
    return false
  }
  const entry: FavoriteLocator = {
    id: key,
    locator_type: loc.locator_type,
    value: loc.value,
    display_name: loc.display_name,
    element_label: context?.elementLabel,
    screen_label: context?.screenLabel,
    package_name: context?.packageName,
    savedAt: new Date().toISOString(),
  }
  list.unshift(entry)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX)))
  return true
}

export function removeFavorite(id: string): void {
  const list = loadFavorites().filter((f) => f.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

export function clearFavorites(): void {
  localStorage.removeItem(STORAGE_KEY)
}
