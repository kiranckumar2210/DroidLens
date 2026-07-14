# DroidLens — Under the Hood

A brief technical overview of how DroidLens works internally: architecture, data flows, and major components.

---

## What DroidLens Is

DroidLens is an **Android UI inspection and automation studio**. It connects to a device over ADB, captures the UI hierarchy and screenshot, helps engineers find reliable locators, generates multi-framework automation code, and records scripts through an **inspector-driven recorder** (similar to Appium Inspector / Katalon Recorder).

---

## High-Level Architecture

**Run locally:** `npm run dev` starts the Python backend (`:8765`) and Vite frontend (`:5173`). Optional Electron shell wraps the same web app.

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENT (Browser or Electron)                               │
│  React UI · Monaco Editor · Session Context · Recorder Hook │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI BACKEND (:8765)                                    │
│  Inspection API · Auth API · Recording API · Live Refresh WS│
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CORE SERVICES                                              │
│  InspectionService · LocatorEngine · CodeGen · RecEngine    │
│  AdbActionExecutionService                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ ADB (platform-tools)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  ANDROID DEVICE                                             │
│  uiautomator dump · screencap · input tap/text/swipe        │
└─────────────────────────────────────────────────────────────┘
```

**How layers connect**

- React UI talks to **Inspection API** for live sessions and element lookup.
- **Recorder Hook** talks to **Recording API** for execute-and-record steps.
- **Auth API** issues JWT tokens and checks license status.
- **InspectionService** and **RecEngine** share the same in-memory hierarchy cache.
- **AdbActionExecutionService** sends shell commands to the device during recording.

---

## Technology Stack

| Layer | Technologies |
|-------|----------------|
| Frontend | React, TypeScript, Vite, Monaco Editor |
| Desktop | Electron (optional) |
| Backend | Python 3, FastAPI, Pydantic |
| Device I/O | ADB — `uiautomator dump`, `screencap`, `input tap/text/swipe` |
| Auth | JWT + refresh tokens, bcrypt, SQLite/JSON repository |
| Payments | Pluggable providers (mock, PhonePe) → license activation via webhook |

---

## Live Inspection Flow

When a user opens a live device session, DroidLens synchronizes the device screen with the inspector (on demand or via auto-refresh).

**Step-by-step**

1. User connects a device or clicks **Refresh** in the inspector.
2. Frontend calls `POST /connect` then `POST /refresh`.
3. **InspectionService** starts a live refresh for that `device_id`.
4. **AndroidAdapter** runs `adb shell uiautomator dump` → raw XML.
5. **AndroidAdapter** runs `adb exec-out screencap` → PNG bytes.
6. **XmlParser** converts XML into an `ElementNode` tree.
7. **CoordinateMapper** builds screenshot ↔ hierarchy dimension mapping.
8. Backend returns `InspectionSession` (tree, screenshot, widths/heights).
9. Frontend renders the screenshot overlay, element tree, and bounds highlights.

**Key files**

- `backend/inspectiq/services/inspection_service.py` — session orchestration
- `backend/inspectiq/adapters/android_adapter.py` — ADB dump/screenshot
- `backend/inspectiq/engine/xml_parser.py` — XML → element tree
- `backend/inspectiq/engine/coordinate_mapper.py` — screenshot ↔ hierarchy coords
- `frontend/src/session/InspectionSessionContext.tsx` — client session state

---

## Element Selection & Locator Generation

Clicking the screenshot or selecting a node in the XML tree resolves the **most specific element** at that point and generates ranked locators.

**Step-by-step**

1. User clicks coordinates `(x, y)` on the screenshot (or selects a tree node by id).
2. `screenshot_to_hierarchy()` maps click coords to hierarchy space.
3. `SmartElementSelector.find_at_coordinates()` picks the deepest, most specific widget (not a parent layout).
4. `LocatorIntelligenceEngine.generate_all()` builds candidate locators (id, text, UiSelector, XPath, relative, etc.).
5. Each locator is scored: **40% stability · 35% uniqueness · 25% maintainability**.
6. Best locators are marked `recommended` and shown in the Inspector panel.
7. User can preview, copy, or use a locator in the Code Generator / Recorder.

**Locator priority (recording & recommendations)**

1. `resource-id`
2. `content-desc` / accessibility id
3. Unique `text`
4. UiSelector / UiAutomator2
5. Relative locators
6. XPath (last resort)

**Key files**

- `backend/inspectiq/engine/element_selector.py`
- `backend/inspectiq/locator/ranker.py`
- `backend/inspectiq/locator/expanded_generators.py`
- `backend/inspectiq/locator/relative_engine.py`

---

## Smart Interaction Recorder Flow

The recorder is a **command recorder**, not a passive touch listener. Every step is initiated from the DroidLens UI.

```
User
  ↓
Select element (screenshot / XML tree / search)
  ↓
Choose action (Click, Send Text, Swipe, Back, Verify, …)
  ↓
Recording Action Panel  →  POST /recording/{id}/execute
  ↓
SmartRecordingEngine.execute_and_record()
  ├─→ LocatorResolutionService  — resolve element + pick best locator
  ├─→ AdbActionExecutionService   — run action on device (adb shell input …)
  ├─→ InspectionService         — refresh XML + screenshot after action
  └─→ CodeGenerationService       — append step code + rebuild full script
  ↓
Updated RecordingSession returned to frontend
  ↓
Timeline + Monaco editor + inspector refreshed
  ↓
Ready for next action
```

**Step-by-step**

1. User clicks **Start Recording** (premium license required).
2. User selects an element in the inspector.
3. User picks an action from the **Action Panel** (e.g. Click).
4. Frontend posts to `POST /recording/{session_id}/execute`.
5. Engine resolves the target element and best locator **before** execution.
6. Engine runs the action on the device via ADB.
7. Engine refreshes hierarchy and screenshot so the inspector stays in sync.
8. Engine appends a `RecordedStep` (action, locator, confidence, code snippet).
9. Frontend updates the timeline and live script in Monaco.

**Recorder services (modular)**

| Service | Responsibility |
|---------|----------------|
| `SmartRecordingEngine` | Session lifecycle, orchestration |
| `AdbActionExecutionService` | Run actions on device |
| `DefaultLocatorResolutionService` | Wraps inspection + locator ranker |
| `DefaultCodeGenerationService` | Per-step + full script assembly |
| `RecordingOptimizer` | Dedupe waits, merge scrolls, prefer stable locators |
| `InMemoryRecordingSessionManager` | Persist sessions to `~/.droidlens/recordings/` |

**Supported codegen profiles:** Python UIAutomator2, Python/Java Appium, Java UIAutomator, JavaScript WebdriverIO, ADB shell.

---

## Code Generation Flow

**Step-by-step**

1. User selects a **recommended locator** and a **language profile** (e.g. `python_uiautomator2`).
2. User chooses an action (click, set_text, wait, assert_exists, …).
3. `MultiLanguageCodeGenerator` maps locator type → framework-specific selector syntax.
4. Generator inserts the action into an idiomatic code template.
5. Output is a script snippet (and optional Page Object class) returned to the UI.

Codegen is **template-based** — it produces runnable script text. Runtime Appium/uiautomator2 drivers are not embedded; the recorder executes actions via **ADB** directly.

---

## Authentication & Licensing

**Step-by-step**

1. User **registers** or **logs in** → receives access + refresh JWT.
2. New accounts get a **trial license** (time-limited premium access).
3. User creates a **payment order** (PhonePe hosted checkout or mock gateway).
4. Payment provider sends a **webhook** on success → backend activates **lifetime license**.
5. Frontend and backend check license on premium routes (`require_premium`, `usePremiumGate`).
6. Premium unlocks: Interaction Recorder, Code Generator, Custom Locator Builder, Session Save, etc.

---

## Backend Module Map

```
backend/inspectiq/
├── api/              # FastAPI routes (main, auth, recording, v1, websocket)
├── adb/              # AdbManager — devices, screencap, shell
├── adapters/         # Android / mock / harmony platform adapters
├── auth/             # Users, JWT, licenses, payments
├── codegen/          # UIAutomator2, Appium, WDIO generators
├── engine/           # XML parser, element selector, coordinate mapper
├── locator/          # Locator strategies, ranker, XPath, relative engine
├── recording/        # Recorder engine + action execution
├── services/         # InspectionService, DeviceService
└── domain/models.py  # Shared Pydantic models
```

---

## Frontend Module Map

```
frontend/src/
├── App.tsx                    # Main inspector layout
├── api/client.ts              # REST client
├── session/                   # InspectionSessionContext + persistence
├── recording/                 # useRecording hook, types, storage
├── components/
│   ├── InspectorPanel.tsx     # Locator details + builder
│   ├── recording/             # Toolbar, timeline, action panel, Monaco
│   └── auth/                  # Login, subscription, checkout
└── data/aboutContent.ts       # About / feature descriptions
```

---

## Data & Persistence

| Data | Where |
|------|--------|
| Auth users / payments | SQLite (`DROIDLENS_AUTH_DB`) or JSON repo |
| License cache | Signed in-memory + DB |
| Recording sessions | `~/.droidlens/recordings/*.json` |
| Inspector UI prefs | `localStorage` / `sessionStorage` |
| Live inspection cache | In-memory `InspectionService._sessions` (per device) |

---

## Design Principles

1. **Single inspection cache** — Recorder and inspector share one `InspectionService` instance so hierarchy and locators stay consistent.
2. **Deterministic recording** — Actions flow through DroidLens UI → ADB execution → locator capture → codegen.
3. **Pluggable architecture** — `ActionExecutionService`, `LocatorResolutionService`, `CodeGenerationService`, and `PaymentProvider` are interface-driven for future Appium runtime, iOS, Flutter, and AI-assisted features.
4. **Coordinate safety** — Screenshot clicks map through `coordinate_mapper` before element lookup; device actions use hierarchy bounds center when available.

---

## Quick API Reference

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Backend + ADB status |
| `POST /connect` | Attach to device |
| `POST /refresh` | New XML + screenshot |
| `POST /select/at` | Inspect element at coordinates |
| `POST /recording/start` | Begin recording session |
| `POST /recording/{id}/execute` | Execute action + record step |
| `GET /recording/{id}/export/script` | Export generated script |
| `POST /auth/login` | JWT session |

Full interactive API docs: `http://127.0.0.1:8765/docs` when the backend is running.

---

*DroidLens v1.0 — See, Inspect, Automate.*
