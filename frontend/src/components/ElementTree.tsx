import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { ElementNode } from '../types'

interface Props {
  tree: ElementNode | null
  selectedId?: string
  onSelect: (id: string) => void
  searchQuery: string
  searchType?: string
}

function nodeMatches(node: ElementNode, q: string, searchType: string): boolean {
  if (!q) return true
  const ql = q.toLowerCase()
  if (searchType === 'text') return (node.text || '').toLowerCase().includes(ql)
  if (searchType === 'resource-id') return (node.resource_id || '').toLowerCase().includes(ql)
  if (searchType === 'class') return (node.class_name || '').toLowerCase().includes(ql)
  const hay = [node.text, node.resource_id, node.class_name, node.content_desc, node.package]
    .filter(Boolean).join(' ').toLowerCase()
  return hay.includes(ql)
}

function subtreeMatches(node: ElementNode, q: string, searchType: string): boolean {
  if (nodeMatches(node, q, searchType)) return true
  return node.children.some((c) => subtreeMatches(c, q, searchType))
}

function TreeNode({
  node, depth, selectedId, onSelect, searchQuery, searchType,
}: {
  node: ElementNode
  depth: number
  selectedId?: string
  onSelect: (id: string) => void
  searchQuery: string
  searchType: string
}) {
  const [expanded, setExpanded] = useState(depth < 2)
  if (searchQuery && !subtreeMatches(node, searchQuery, searchType)) return null

  const label = node.text || node.resource_id?.split('/').pop() || node.class_name.split('.').pop() || 'node'
  const hasChildren = node.children.length > 0
  const isSelected = node.id === selectedId
  const shortClass = node.class_name.split('.').pop()

  return (
    <div className="tree-branch">
      <div
        className={`tree-node ${isSelected ? 'selected' : ''} ${node.is_flutter ? 'flutter-node' : ''}`}
        style={{ paddingLeft: depth * 14 + 6 }}
        onClick={() => onSelect(node.id)}
        role="treeitem"
        aria-selected={isSelected}
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter') onSelect(node.id) }}
      >
        {hasChildren ? (
          <button
            type="button"
            className="tree-toggle"
            aria-label={expanded ? 'Collapse' : 'Expand'}
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        ) : (
          <span className="tree-toggle empty" />
        )}
        <span className="tree-class">{shortClass}</span>
        {label !== shortClass && <span className="tree-label">&quot;{label}&quot;</span>}
        {node.is_flutter && <span className="flutter-badge">Flutter</span>}
      </div>
      {expanded && hasChildren && (
        <div role="group">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              searchQuery={searchQuery}
              searchType={searchType}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function ElementTree({ tree, selectedId, onSelect, searchQuery, searchType = 'all' }: Props) {
  if (!tree) {
    return (
      <div className="panel tree-panel fill-panel">
        <div className="panel-header">UI Hierarchy</div>
        <div className="empty-state">No hierarchy loaded</div>
      </div>
    )
  }

  return (
    <div className="panel tree-panel fill-panel" role="tree" aria-label="UI element hierarchy">
      <div className="panel-header">
        <span>UI Hierarchy</span>
      </div>
      <div className="tree-content">
        <TreeNode
          node={tree}
          depth={0}
          selectedId={selectedId}
          onSelect={onSelect}
          searchQuery={searchQuery}
          searchType={searchType}
        />
      </div>
    </div>
  )
}
