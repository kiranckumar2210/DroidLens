import type { Bounds, ElementNode } from '../types'

export function countElements(root: ElementNode | null | undefined): number {
  if (!root) return 0
  let n = 1
  for (const c of root.children) n += countElements(c)
  return n
}

export function findNodesByIds(root: ElementNode | null | undefined, ids: string[]): ElementNode[] {
  if (!root || !ids.length) return []
  const wanted = new Set(ids)
  const found: ElementNode[] = []

  const walk = (node: ElementNode) => {
    if (wanted.has(node.id) || (node.stable_key && wanted.has(node.stable_key))) {
      found.push(node)
    }
    node.children.forEach(walk)
  }
  walk(root)
  return found
}

export function boundsToPct(bounds: Bounds, hierarchyWidth: number, hierarchyHeight: number) {
  const w = hierarchyWidth || 1
  const h = hierarchyHeight || 1
  return {
    left: `${(bounds.x1 / w) * 100}%`,
    top: `${(bounds.y1 / h) * 100}%`,
    width: `${((bounds.x2 - bounds.x1) / w) * 100}%`,
    height: `${((bounds.y2 - bounds.y1) / h) * 100}%`,
  }
}

/** Map a click on the displayed screenshot to screenshot pixel coordinates. */
export function clientToScreenshotPixels(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  screenshotWidth: number,
  screenshotHeight: number,
): { x: number; y: number } | null {
  if (!rect.width || !rect.height) return null
  const x = Math.round((clientX - rect.left) * (screenshotWidth / rect.width))
  const y = Math.round((clientY - rect.top) * (screenshotHeight / rect.height))
  if (x < 0 || y < 0 || x > screenshotWidth || y > screenshotHeight) return null
  return { x, y }
}
