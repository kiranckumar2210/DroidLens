import type { LucideIcon } from 'lucide-react'
import {
  CircleDot, Code2, Cpu, Layers, Monitor, Palette, Smartphone, Target, Upload,
} from 'lucide-react'

export interface FeatureCategory {
  id: string
  title: string
  icon: LucideIcon
  items: string[]
}

export const ABOUT_DESCRIPTION =
  'DroidLens is a professional Android UI Inspection and Automation Studio designed for QA engineers, automation engineers, mobile developers, and testers. It provides powerful tools to inspect Android user interfaces, generate robust locators, build automation scripts, and accelerate mobile automation development using modern workflows.\n\nThe application supports both Live Device Inspection and Offline XML Inspection, making it suitable for day-to-day automation development and debugging.\n\nThe Smart Interaction Recorder lets you build production-ready automation scripts from the inspector itself — select elements, execute actions on your device, and watch code generate live in the timeline, similar to Appium Inspector or Katalon Studio Recorder.'

export const FEATURE_CATEGORIES: FeatureCategory[] = [
  {
    id: 'live',
    title: 'Live Inspection',
    icon: Monitor,
    items: [
      'Live Android Device Inspection',
      'USB & Wireless ADB Support',
      'Android Emulator Support',
      'Real-time Screenshot Capture',
      'Live XML Hierarchy Inspection',
      'Automatic Refresh',
      'Element Highlighting',
      'Bounds Visualization',
    ],
  },
  {
    id: 'offline',
    title: 'Offline Inspection',
    icon: Upload,
    items: [
      'Open Saved XML Dumps',
      'Open Screenshot + XML',
      'Mock Demo Project',
      'Offline Element Inspection',
      'XML Tree Navigation',
    ],
  },
  {
    id: 'locator',
    title: 'Locator Engine',
    icon: Target,
    items: [
      'Smart Locator Suggestions',
      'XPath Generation',
      'Relative XPath Generation',
      'UiSelector Generation',
      'Relative Locator Builder',
      'Parent / Child / Ancestor / Descendant Locators',
      'Following & Preceding Sibling Locators',
      'Composite Locator Suggestions',
      'Locator Reliability Score',
      'Live Locator Validation',
    ],
  },
  {
    id: 'builder',
    title: 'Custom Locator Builder',
    icon: Code2,
    items: [
      'Monaco Editor Integration',
      'XPath Validation',
      'UiSelector Validation',
      'Auto-completion',
      'Syntax Highlighting',
      'Real-time Element Matching',
      'Match Count Preview',
      'Error Highlighting',
    ],
  },
  {
    id: 'recorder',
    title: 'Smart Interaction Recorder',
    icon: CircleDot,
    items: [
      'Inspector-driven command recording (no passive touch capture)',
      'Select elements from screenshot, XML tree, or search',
      'Contextual Action Panel — Click, Text, Gestures, Waits, Validation',
      'Executes actions on device via ADB (Appium-compatible semantics)',
      'Automatic locator resolution with confidence scores',
      'Live code generation — UIAutomator2, Appium, Java, WebdriverIO',
      'Recording timeline with step status and execution time',
      'Undo, redo, delete, export script, copy to clipboard',
      'Automatic waits — no hard-coded sleep statements',
      'Premium feature — requires lifetime or trial license',
    ],
  },
  {
    id: 'codegen',
    title: 'Code Generator',
    icon: Layers,
    items: [
      'Python UIAutomator2',
      'Python Appium',
      'Java UIAutomator',
      'Java Appium',
      'JavaScript Appium',
      'WebdriverIO',
      'Click, Long Click, Send Text, Swipe, Scroll',
      'Wait, Assertions, Screenshot, Navigation',
      'Page Object snippets',
    ],
  },
  {
    id: 'device',
    title: 'Device Management',
    icon: Smartphone,
    items: [
      'Automatic Device Detection',
      'Multiple Device Support',
      'Device Information',
      'Android Version Detection',
      'Connection Status',
      'Wireless ADB',
    ],
  },
  {
    id: 'productivity',
    title: 'Productivity',
    icon: Palette,
    items: [
      'Modern Dark & Light Themes',
      'Search & Filter',
      'XML Search',
      'Responsive Dashboard',
      'Session Management',
      'Premium Licensing',
      'Mock Payment Integration',
      'Future Plugin Support',
    ],
  },
]

export const TECH_STACK = [
  'React & TypeScript',
  'Electron (Desktop)',
  'Python & FastAPI',
  'Android Debug Bridge (ADB)',
  'UIAutomator2 & Appium',
  'Monaco Editor',
  'XPath Engine',
  'Modern Material Design UI',
]

export const RELEASE_NOTES_V1 = [
  'Initial release — Live & offline Android UI inspection',
  'Smart locator engine with reliability scoring',
  'Custom locator builder with Monaco editor',
  'Multi-framework code generator',
  'Smart Interaction Recorder — inspector-driven action recording studio',
  'Guest, trial, and lifetime licensing with mock payment gateway',
  'Dark & light themes with responsive dashboard',
]

export const RELEASE_NOTES_V11 = [
  'Locator export — JSON, CSV, and Markdown for current element or full repository',
  'Favorite locators — star and reuse locators across sessions',
  'Recent Sessions — restore live devices, offline packages, or sample data',
  'Package notes — annotate offline XML screens; included in metadata export',
  'Keyboard shortcuts — F5 refresh, Ctrl+F search, Ctrl+Shift+E export, Ctrl+L live refresh toggle',
]

export const RELEASE_NOTES_V12 = [
  'XML Diff — compare two UIAutomator dumps; see added, removed, and changed elements',
  'Locator Health Scan — detect fragile locators, duplicate resource-ids, missing labels',
  'Batch folder health scan in desktop app',
  'Recording Studio — export Page Object Model + pytest test file (POM button)',
]

export const RELEASE_NOTES_V13 = [
  'Locator suite validation — JSON format + UI dialog for CI-style checks',
  'CLI tools: droidlens validate-locators, validate-folder, health-scan',
  'Locator Migration Assistant — suggest replacements when UI hierarchy changes',
  'Export health scan reports as JSON',
]
