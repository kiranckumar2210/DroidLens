import type { CSSProperties } from 'react'
import type { Bounds } from '../types'

/** Single coordinate system definition shared by overlays and hit-testing. */
export interface CoordinateMapping {
  /** XML / UIAutomator bounds space */
  hierarchyWidth: number
  hierarchyHeight: number
  /** PNG pixel space (must match loaded image naturalWidth/Height) */
  screenshotWidth: number
  screenshotHeight: number
  /** Optional origin offset when hierarchy root != screenshot origin */
  offsetX: number
  offsetY: number
  scaleX: number
  scaleY: number
}

export interface Point {
  x: number
  y: number
}

export interface DisplayRect {
  left: number
  top: number
  width: number
  height: number
}

export interface HitTestDebug {
  rawClient: Point
  displayRect: DisplayRect
  containerScroll: Point
  panOffset: Point
  zoom: number
  screenshotPixel: Point | null
  hierarchyPixel: Point | null
  mapping: CoordinateMapping
}

export function buildMapping(
  hierarchyWidth: number,
  hierarchyHeight: number,
  screenshotWidth: number,
  screenshotHeight: number,
  offsetX = 0,
  offsetY = 0,
): CoordinateMapping {
  const hw = hierarchyWidth || 1
  const hh = hierarchyHeight || 1
  const sw = screenshotWidth || hw
  const sh = screenshotHeight || hh
  return {
    hierarchyWidth: hw,
    hierarchyHeight: hh,
    screenshotWidth: sw,
    screenshotHeight: sh,
    offsetX,
    offsetY,
    scaleX: hw / sw,
    scaleY: hh / sh,
  }
}

/**
 * Map viewport mouse position to screenshot PNG pixel coordinates.
 * Uses the rendered image rect (includes pan/zoom transforms) and native PNG dimensions.
 */
export function displayToScreenshot(
  clientX: number,
  clientY: number,
  imageRect: DisplayRect,
  nativeWidth: number,
  nativeHeight: number,
): Point | null {
  if (!imageRect.width || !imageRect.height || !nativeWidth || !nativeHeight) {
    return null
  }
  const relX = clientX - imageRect.left
  const relY = clientY - imageRect.top
  if (relX < 0 || relY < 0 || relX > imageRect.width || relY > imageRect.height) {
    return null
  }
  return {
    x: Math.round((relX / imageRect.width) * nativeWidth),
    y: Math.round((relY / imageRect.height) * nativeHeight),
  }
}

export function screenshotToHierarchy(
  x: number,
  y: number,
  mapping: CoordinateMapping,
): Point {
  const { hierarchyWidth, hierarchyHeight, screenshotWidth, screenshotHeight, offsetX, offsetY } = mapping
  if (!screenshotWidth || !screenshotHeight) {
    return { x: Math.round(x), y: Math.round(y) }
  }
  const hx = Math.round(x * (hierarchyWidth / screenshotWidth) + offsetX)
  const hy = Math.round(y * (hierarchyHeight / screenshotHeight) + offsetY)
  return {
    x: Math.max(0, Math.min(hx, Math.max(hierarchyWidth - 1, 0))),
    y: Math.max(0, Math.min(hy, Math.max(hierarchyHeight - 1, 0))),
  }
}

export function hierarchyToScreenshot(bounds: Bounds, mapping: CoordinateMapping): Bounds {
  const sx = mapping.screenshotWidth / mapping.hierarchyWidth
  const sy = mapping.screenshotHeight / mapping.hierarchyHeight
  return {
    x1: Math.round((bounds.x1 - mapping.offsetX) * sx),
    y1: Math.round((bounds.y1 - mapping.offsetY) * sy),
    x2: Math.round((bounds.x2 - mapping.offsetX) * sx),
    y2: Math.round((bounds.y2 - mapping.offsetY) * sy),
  }
}

/** CSS overlay percentages on a box sized to native screenshot dimensions. */
export function boundsToOverlayStyle(bounds: Bounds, mapping: CoordinateMapping): CSSProperties {
  const ss = hierarchyToScreenshot(bounds, mapping)
  const sw = mapping.screenshotWidth || 1
  const sh = mapping.screenshotHeight || 1
  return {
    left: `${(ss.x1 / sw) * 100}%`,
    top: `${(ss.y1 / sh) * 100}%`,
    width: `${((ss.x2 - ss.x1) / sw) * 100}%`,
    height: `${((ss.y2 - ss.y1) / sh) * 100}%`,
  }
}

export function boundsCenter(bounds: Bounds): Point {
  return {
    x: Math.round((bounds.x1 + bounds.x2) / 2),
    y: Math.round((bounds.y1 + bounds.y2) / 2),
  }
}

export function buildHitTestDebug(
  clientX: number,
  clientY: number,
  imageRect: DisplayRect,
  nativeWidth: number,
  nativeHeight: number,
  mapping: CoordinateMapping,
  containerScroll: Point,
  panOffset: Point,
  zoom: number,
): HitTestDebug {
  const screenshotPixel = displayToScreenshot(clientX, clientY, imageRect, nativeWidth, nativeHeight)
  const hierarchyPixel = screenshotPixel ? screenshotToHierarchy(screenshotPixel.x, screenshotPixel.y, mapping) : null
  return {
    rawClient: { x: clientX, y: clientY },
    displayRect: imageRect,
    containerScroll,
    panOffset,
    zoom,
    screenshotPixel,
    hierarchyPixel,
    mapping,
  }
}
