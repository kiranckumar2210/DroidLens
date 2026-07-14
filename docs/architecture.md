# DroidLens — System Architecture

**DroidLens** (*See. Inspect. Automate.*) is a professional Android UI inspection and automation platform with intelligent locator generation, ranking, and script output.

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│  DroidLens Desktop / Web UI (React + Vite)                  │
│  Dashboard · Inspector · Locator Engine · Code Generator    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI Backend (inspectiq Python package)                 │
│  InspectionService · LocatorIntelligenceEngine · Codegen    │
└──────────────────────────┬──────────────────────────────────┘
                           │ ADB
┌──────────────────────────▼──────────────────────────────────┐
│  Android Device / Emulator                                  │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

| Module | Responsibility |
|--------|----------------|
| `adb/` | Device discovery, screencap, UI dump, multi-display |
| `adapters/` | Platform-specific XML parsing (Android production) |
| `engine/` | Element tree, coordinate hit-testing, hierarchy context |
| `locator/` | Expanded generators, relative locators, validation |
| `codegen/` | uiautomator2, Appium multi-language output |
| `services/` | Session orchestration (live / offline / mock) |
| `storage/` | SQLite locator repository at `~/.droidlens/` |

## Session Modes

- **Live** — Real ADB device; strict separation from mock data
- **Offline** — Uploaded XML + optional screenshot
- **Mock** — Bundled sample for demos and tests

## Locator Intelligence

1. Attribute-based strategies (resource-id, text, description, class, …)
2. Composite and boolean combinations
3. Relative / context-aware locators (parent, sibling, ancestor)
4. Scoring: stability, uniqueness, maintainability
5. Live validation against loaded hierarchy

## Data Storage

- SQLite at `~/.droidlens/droidlens.db`
- Legacy path `~/.inspectiq/` supported for migration
