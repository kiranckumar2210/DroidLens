import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Bug, Maximize2, Move, RotateCcw, ZoomIn, ZoomOut,
} from 'lucide-react'
import type { ElementNode } from '../types'
import {
  boundsCenter,
  boundsToOverlayStyle,
  buildHitTestDebug,
  buildMapping,
  displayToScreenshot,
  hierarchyToScreenshot,
  type CoordinateMapping,
  type HitTestDebug,
} from '../utils/coordinateMapper'
import { findNodesByIds } from '../utils/treeUtils'

export type ZoomMode = 'fit' | 'actual' | 'custom'

interface Props {
  screenshot?: string | null
  screenshotWidth: number
  screenshotHeight: number
  hierarchyWidth: number
  hierarchyHeight: number
  tree?: ElementNode | null
  selectedElement?: ElementNode | null
  highlightIds?: string[]
  onClickCoords: (x: number, y: number) => void
  onZoomChange?: (zoom: number) => void
  onCursorMove?: (x: number, y: number) => void
  onDebugHitTest?: (debug: HitTestDebug) => void
  compactHeader?: boolean
}

interface ViewportMetrics {
  containerW: number
  containerH: number
  scrollTop: number
  scrollLeft: number
  contentW: number
  contentH: number
  imageTop: number
  imageLeft: number
}

function flattenVisibleNodes(root: ElementNode | null | undefined, limit = 150): ElementNode[] {
  if (!root) return []
  const out: ElementNode[] = []
  const walk = (node: ElementNode) => {
    if (out.length >= limit) return
    if (node.bounds && (node.clickable || node.text || node.resource_id)) {
      out.push(node)
    }
    node.children.forEach(walk)
  }
  walk(root)
  return out
}

export default function ScreenshotPanel({
  screenshot,
  screenshotWidth,
  screenshotHeight,
  hierarchyWidth,
  hierarchyHeight,
  tree,
  selectedElement,
  highlightIds = [],
  onClickCoords,
  onZoomChange,
  onCursorMove,
  onDebugHitTest,
  compactHeader = false,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const [zoom, setZoom] = useState(1)
  const [zoomMode, setZoomMode] = useState<ZoomMode>('fit')
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [debugMode, setDebugMode] = useState(false)
  const [nativeSize, setNativeSize] = useState<{ w: number; h: number } | null>(null)
  const [lastClick, setLastClick] = useState<{ x: number; y: number } | null>(null)
  const [hitDebug, setHitDebug] = useState<HitTestDebug | null>(null)
  const [viewportMetrics, setViewportMetrics] = useState<ViewportMetrics | null>(null)
  const panStart = useRef<{ x: number; y: number; px: number; py: number } | null>(null)
  const spaceDown = useRef(false)
  const panMoved = useRef(false)

  const pngWidth = nativeSize?.w || screenshotWidth || 1
  const pngHeight = nativeSize?.h || screenshotHeight || 1

  const mapping: CoordinateMapping = useMemo(
    () => buildMapping(hierarchyWidth, hierarchyHeight, pngWidth, pngHeight),
    [hierarchyWidth, hierarchyHeight, pngWidth, pngHeight],
  )

  const dimensionMismatch = nativeSize && (
    nativeSize.w !== screenshotWidth || nativeSize.h !== screenshotHeight
  )

  const displayW = pngWidth * zoom
  const displayH = pngHeight * zoom

  const resetScroll = useCallback(() => {
    const c = containerRef.current
    if (!c) return
    c.scrollTop = 0
    c.scrollLeft = 0
  }, [])

  const updateViewportMetrics = useCallback(() => {
    const c = containerRef.current
    const img = imgRef.current
    if (!c) return
    const cRect = c.getBoundingClientRect()
    const iRect = img?.getBoundingClientRect()
    setViewportMetrics({
      containerW: c.clientWidth,
      containerH: c.clientHeight,
      scrollTop: c.scrollTop,
      scrollLeft: c.scrollLeft,
      contentW: displayW,
      contentH: displayH,
      imageTop: iRect ? iRect.top - cRect.top + c.scrollTop : 0,
      imageLeft: iRect ? iRect.left - cRect.left + c.scrollLeft : 0,
    })
  }, [displayW, displayH])

  useEffect(() => {
    setNativeSize(null)
    setLastClick(null)
    setHitDebug(null)
    setPan({ x: 0, y: 0 })
    resetScroll()
  }, [screenshot, resetScroll])

  const applyZoom = useCallback((z: number, mode: ZoomMode = 'custom') => {
    const clamped = Math.min(4, Math.max(0.05, z))
    setZoom(clamped)
    setZoomMode(mode)
    onZoomChange?.(clamped)
  }, [onZoomChange])

  const fitToWindow = useCallback(() => {
    const c = containerRef.current
    if (!c || !pngWidth || !pngHeight) return
    const pad = 24
    const zw = (c.clientWidth - pad) / pngWidth
    const zh = (c.clientHeight - pad) / pngHeight
    const fitZoom = Math.min(zw, zh)
    applyZoom(Math.min(fitZoom, 1), 'fit')
    setPan({ x: 0, y: 0 })
    requestAnimationFrame(resetScroll)
  }, [pngWidth, pngHeight, applyZoom, resetScroll])

  useEffect(() => {
    if (zoomMode === 'fit') fitToWindow()
  }, [screenshot, pngWidth, pngHeight, fitToWindow, zoomMode])

  useEffect(() => {
    const onResize = () => {
      if (zoomMode === 'fit') fitToWindow()
      updateViewportMetrics()
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [fitToWindow, zoomMode, updateViewportMetrics])

  useEffect(() => {
    updateViewportMetrics()
  }, [displayW, displayH, pan, debugMode, updateViewportMetrics])

  useEffect(() => {
    const c = containerRef.current
    if (!c) return
    const onScroll = () => updateViewportMetrics()
    c.addEventListener('scroll', onScroll, { passive: true })
    return () => c.removeEventListener('scroll', onScroll)
  }, [updateViewportMetrics])

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code === 'Space') spaceDown.current = true
      if (e.code === 'KeyD' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const t = e.target as HTMLElement
        if (t.tagName !== 'INPUT' && t.tagName !== 'TEXTAREA') {
          setDebugMode((v) => !v)
        }
      }
    }
    const up = (e: KeyboardEvent) => { if (e.code === 'Space') spaceDown.current = false }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => { window.removeEventListener('keydown', down); window.removeEventListener('keyup', up) }
  }, [])

  const handleImageLoad = () => {
    const img = imgRef.current
    if (!img?.naturalWidth) return
    setNativeSize({ w: img.naturalWidth, h: img.naturalHeight })
    requestAnimationFrame(() => {
      resetScroll()
      updateViewportMetrics()
    })
  }

  const resolveHitTest = useCallback((clientX: number, clientY: number) => {
    const img = imgRef.current
    const container = containerRef.current
    if (!img || !img.naturalWidth) return null

    const rect = img.getBoundingClientRect()
    const imageRect = { left: rect.left, top: rect.top, width: rect.width, height: rect.height }
    const screenshotPixel = displayToScreenshot(
      clientX, clientY, imageRect, img.naturalWidth, img.naturalHeight,
    )
    const debug = buildHitTestDebug(
      clientX,
      clientY,
      imageRect,
      img.naturalWidth,
      img.naturalHeight,
      mapping,
      {
        x: container?.scrollLeft ?? 0,
        y: container?.scrollTop ?? 0,
      },
      pan,
      zoom,
    )
    if (debugMode) setHitDebug(debug)
    onDebugHitTest?.(debug)
    return screenshotPixel
  }, [mapping, pan, zoom, onDebugHitTest, debugMode])

  const handleClick = (e: React.MouseEvent) => {
    if (spaceDown.current || panMoved.current) return
    const pt = resolveHitTest(e.clientX, e.clientY)
    if (pt) {
      setLastClick(pt)
      onClickCoords(pt.x, pt.y)
    }
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    applyZoom(zoom + (e.deltaY > 0 ? -0.1 : 0.1), 'custom')
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    panMoved.current = false
    if (e.button === 1 || spaceDown.current || (e.button === 0 && e.altKey)) {
      panStart.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    const pt = resolveHitTest(e.clientX, e.clientY)
    if (pt) onCursorMove?.(pt.x, pt.y)
    if (panStart.current) {
      const dx = e.clientX - panStart.current.x
      const dy = e.clientY - panStart.current.y
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) panMoved.current = true
      setPan({
        x: panStart.current.px + dx,
        y: panStart.current.py + dy,
      })
    }
  }

  const handleMouseUp = () => { panStart.current = null }

  const matchOverlays = useMemo(() => {
    const nodes = findNodesByIds(tree, highlightIds)
    return nodes
      .filter((n) => n.bounds && n.id !== selectedElement?.id)
      .map((n) => ({
        id: n.id,
        style: boundsToOverlayStyle(n.bounds!, mapping),
      }))
  }, [tree, highlightIds, selectedElement?.id, mapping])

  const selectedOverlay = selectedElement?.bounds
    ? boundsToOverlayStyle(selectedElement.bounds, mapping)
    : null

  const debugNodes = useMemo(
    () => (debugMode ? flattenVisibleNodes(tree) : []),
    [debugMode, tree],
  )

  const clickOverlayStyle = lastClick && pngWidth && pngHeight ? {
    left: `${(lastClick.x / pngWidth) * 100}%`,
    top: `${(lastClick.y / pngHeight) * 100}%`,
  } : null

  const contentOverflows = viewportMetrics
    && (viewportMetrics.contentH > viewportMetrics.containerH
      || viewportMetrics.contentW > viewportMetrics.containerW)

  return (
    <div className="panel screenshot-panel">
      <div className={`panel-header ${compactHeader ? 'compact-header' : ''}`}>
        {!compactHeader && <span>Screenshot</span>}
        <div className="panel-header-actions zoom-toolbar">
          <button
            type="button"
            className={`btn-icon copy-btn ${debugMode ? 'debug-active' : ''}`}
            title="Toggle viewport debug (D)"
            onClick={() => setDebugMode((v) => !v)}
          >
            <Bug size={14} />
          </button>
          <button type="button" className="btn-icon copy-btn" title="Zoom out" onClick={() => applyZoom(zoom - 0.15)}>
            <ZoomOut size={14} />
          </button>
          <span className="zoom-label">{Math.round(zoom * 100)}%</span>
          <button type="button" className="btn-icon copy-btn" title="Zoom in" onClick={() => applyZoom(zoom + 0.15)}>
            <ZoomIn size={14} />
          </button>
          <button type="button" className="btn-icon copy-btn" title="Fit to window" onClick={fitToWindow}>
            <Maximize2 size={14} />
          </button>
          <button type="button" className="btn-icon copy-btn" title="Actual size (100%)" onClick={() => { applyZoom(1, 'actual'); setPan({ x: 0, y: 0 }); requestAnimationFrame(resetScroll) }}>
            1:1
          </button>
          <button type="button" className="btn-icon copy-btn" title="Reset pan & scroll" onClick={() => { setPan({ x: 0, y: 0 }); resetScroll() }}>
            <RotateCcw size={14} />
          </button>
          <span className="pan-hint" title="Hold Space or Alt+drag to pan"><Move size={12} /></span>
        </div>
      </div>

      <div
        ref={containerRef}
        className="screenshot-container"
        onClick={handleClick}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {debugMode && (
          <div className="screenshot-viewport-debug" aria-hidden>
            <div className="viewport-debug-label">Viewport</div>
          </div>
        )}

        {screenshot ? (
          <div className="screenshot-scroll-content">
            <div
              className="screenshot-stage"
              style={{ transform: `translate(${pan.x}px, ${pan.y}px)` }}
            >
              <div
                className="screenshot-wrapper"
                style={{ width: displayW, height: displayH }}
              >
                {debugMode && (
                  <>
                    <div className="screenshot-image-debug-border" />
                    <div className="screenshot-origin-marker" title="Image origin (0,0)" />
                  </>
                )}
                <img
                  ref={imgRef}
                  src={`data:image/png;base64,${screenshot}`}
                  alt="Device screenshot"
                  className="screenshot-img"
                  width={pngWidth}
                  height={pngHeight}
                  style={{ width: displayW, height: displayH }}
                  draggable={false}
                  onLoad={handleImageLoad}
                />
                {debugMode && debugNodes.map((n) => n.bounds && (
                  <div
                    key={`dbg-${n.id}`}
                    className="element-overlay debug-bounds-overlay"
                    style={boundsToOverlayStyle(n.bounds, mapping)}
                    title={n.text || n.resource_id || n.class_name}
                  />
                ))}
                {debugMode && debugNodes.map((n) => n.bounds && (
                  <div
                    key={`ctr-${n.id}`}
                    className="debug-center-dot"
                    style={{
                      left: `${(boundsCenter(hierarchyToScreenshot(n.bounds, mapping)).x / pngWidth) * 100}%`,
                      top: `${(boundsCenter(hierarchyToScreenshot(n.bounds, mapping)).y / pngHeight) * 100}%`,
                    }}
                  />
                ))}
                {matchOverlays.map((o) => (
                  <div key={o.id} className="element-overlay match-overlay" style={o.style} />
                ))}
                {selectedOverlay && (
                  <div className="element-overlay selected-overlay" style={selectedOverlay} />
                )}
                {debugMode && clickOverlayStyle && (
                  <div className="debug-click-marker" style={clickOverlayStyle} />
                )}
                {debugMode && hitDebug?.screenshotPixel && (
                  <div
                    className="debug-cursor-marker"
                    style={{
                      left: `${(hitDebug.screenshotPixel.x / pngWidth) * 100}%`,
                      top: `${(hitDebug.screenshotPixel.y / pngHeight) * 100}%`,
                    }}
                  />
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state">Connect a device or upload a screenshot to begin inspection</div>
        )}
      </div>

      {debugMode && (
        <div className="coord-debug-panel">
          <div className="coord-debug-row">
            <span className="coord-debug-label">Captured PNG</span>
            <code>{pngWidth}×{pngHeight}</code>
            {dimensionMismatch && (
              <span className="coord-debug-warn">session {screenshotWidth}×{screenshotHeight}</span>
            )}
          </div>
          <div className="coord-debug-row">
            <span className="coord-debug-label">Rendered</span>
            <code>{Math.round(displayW)}×{Math.round(displayH)} @ {Math.round(zoom * 100)}%</code>
          </div>
          {viewportMetrics && (
            <>
              <div className="coord-debug-row">
                <span className="coord-debug-label">Viewport</span>
                <code>{viewportMetrics.containerW}×{viewportMetrics.containerH}</code>
              </div>
              <div className="coord-debug-row">
                <span className="coord-debug-label">Scroll</span>
                <code>({viewportMetrics.scrollLeft}, {viewportMetrics.scrollTop})</code>
              </div>
              <div className="coord-debug-row">
                <span className="coord-debug-label">Overflow</span>
                <code className={contentOverflows ? 'coord-debug-warn' : ''}>
                  {contentOverflows ? 'yes — scroll to see full image' : 'no — full image visible'}
                </code>
              </div>
            </>
          )}
          <div className="coord-debug-row">
            <span className="coord-debug-label">Hierarchy</span>
            <code>{mapping.hierarchyWidth}×{mapping.hierarchyHeight}</code>
          </div>
          {hitDebug && (
            <>
              <div className="coord-debug-row">
                <span className="coord-debug-label">Screenshot px</span>
                <code>
                  {hitDebug.screenshotPixel
                    ? `(${hitDebug.screenshotPixel.x}, ${hitDebug.screenshotPixel.y})`
                    : '—'}
                </code>
              </div>
              <div className="coord-debug-row">
                <span className="coord-debug-label">Hierarchy px</span>
                <code>
                  {hitDebug.hierarchyPixel
                    ? `(${hitDebug.hierarchyPixel.x}, ${hitDebug.hierarchyPixel.y})`
                    : '—'}
                </code>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
