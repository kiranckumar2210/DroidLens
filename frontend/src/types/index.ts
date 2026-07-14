export type Platform = 'android' | 'ios' | 'harmonyos'
export type SessionMode = 'live' | 'offline'

export interface Bounds {
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface ElementNode {
  id: string
  stable_key?: string | null
  platform: Platform
  class_name: string
  text?: string | null
  resource_id?: string | null
  accessibility_id?: string | null
  content_desc?: string | null
  hint?: string | null
  package?: string | null
  bounds?: Bounds | null
  enabled: boolean
  visible: boolean
  clickable: boolean
  scrollable: boolean
  focusable: boolean
  focused: boolean
  checkable: boolean
  checked: boolean
  selected: boolean
  password: boolean
  long_clickable: boolean
  drawing_order?: number | null
  index: number
  instance: number
  depth: number
  is_flutter: boolean
  flutter_semantics?: string | null
  children: ElementNode[]
}

export interface LocatorScore {
  stability: number
  uniqueness: number
  maintainability: number
  overall: number
}

export interface LocatorCandidate {
  locator_type: string
  value: string
  display_name: string
  scores: LocatorScore
  recommended: boolean
  reason: string
  match_count?: number
  framework_hint?: string
  export_formats?: Record<string, string>
  performance_rating?: string | null
  robustness?: string | null
  valid?: boolean | null
  category?: string | null
  badge?: string | null
  star_rating?: number | null
  layout_dependency?: number | null
  is_duplicate?: boolean
}

export interface ElementAnalysisContext {
  element_id: string
  hierarchy_level: number
  ancestor_count: number
  sibling_count: number
  child_count: number
  parent_class?: string | null
  parent_resource_id?: string | null
  is_in_recyclerview: boolean
  is_in_scrollable: boolean
  has_dynamic_text: boolean
  has_dynamic_resource_id: boolean
  duplicate_resource_ids_in_tree: number
  stable_attributes: string[]
}

export interface LocatorSuggestion {
  severity: string
  category: string
  message: string
  hint?: string | null
}

export interface LocatorGroup {
  category: string
  label: string
  locators: LocatorCandidate[]
}

export interface LocatorBundle {
  element: ElementNode
  analysis: ElementAnalysisContext
  groups: LocatorGroup[]
  all_locators: LocatorCandidate[]
  suggestions: LocatorSuggestion[]
  recommended?: LocatorCandidate | null
  xpath_examples: XPathExample[]
  generation_ms: number
  tree_hash: string
}

export interface LocatorComparisonResult {
  locator_a: LocatorCandidate
  locator_b: LocatorCandidate
  matches_a: number
  matches_b: number
  overlap_count: number
  faster?: string | null
  more_stable?: string | null
  recommendation: string
}

export interface XPathExample {
  axis: string
  xpath: string
  description: string
}

export interface DeviceInfo {
  id: string
  platform: Platform
  name: string
  model?: string
  manufacturer?: string
  os_version?: string
  sdk_version?: string
  status: string
  connection_type: string
  serial?: string
  resolution?: string
  orientation?: string
  battery_level?: number
  is_emulator: boolean
}

export interface AdbStatus {
  installed: boolean
  path?: string
  version?: string
  server_running: boolean
  device_count: number
  unauthorized_count: number
  offline_count: number
}

export interface ElementInspectionResult {
  element: ElementNode
  parent?: ElementNode | null
  children: ElementNode[]
  locators: LocatorCandidate[]
  xpath_examples: XPathExample[]
  coordinate_fallback?: LocatorCandidate | null
  hierarchy_level: number
  analysis?: ElementAnalysisContext | null
  suggestions?: LocatorSuggestion[]
  grouped_locators?: LocatorGroup[]
  locator_bundle?: LocatorBundle | null
}

export interface InspectionSession {
  device_id: string
  platform: Platform
  mode: SessionMode
  tree?: ElementNode | null
  screenshot_base64?: string | null
  raw_xml?: string | null
  screen_width: number
  screen_height: number
  screenshot_width: number
  screenshot_height: number
  rotation: number
  scale_factor: number
  coordinate_mapping?: Record<string, number> | null
  last_refresh_ms?: number | null
}

export interface GeneratedScript {
  language: string
  framework: string
  code: string
  locator_used: LocatorCandidate
  page_object?: string | null
}

export interface CustomLocatorRule {
  attribute: string
  operator: string
  value: string
}

export interface CustomLocatorResult {
  xpath: string
  uiautomator2: string
  match_count: number
  matched_elements: ElementNode[]
}
