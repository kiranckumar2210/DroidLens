# DroidLens Platform Guide

**Version:** 2.0.0 · **Product:** DroidLens — *See. Inspect. Automate.*

This guide explains how to inspect UI on **Android**, **iOS**, **HarmonyOS**, and **cloud device farms**, plus the **offline XML + PNG** workflow that works on every platform without a connected device.

---

## Table of contents

1. [Quick start](#1-quick-start)
2. [Dashboard overview](#2-dashboard-overview)
3. [Android (live)](#3-android-live)
4. [iOS (live)](#4-ios-live)
5. [HarmonyOS (live)](#5-harmonyos-live)
6. [Cloud device farm (Appium)](#6-cloud-device-farm-appium)
7. [Offline XML packages](#7-offline-xml-packages)
8. [Sample / mock projects](#8-sample--mock-projects)
9. [Inspector workflow (all platforms)](#9-inspector-workflow-all-platforms)
10. [Locators by platform](#10-locators-by-platform)
11. [Environment variables](#11-environment-variables)
12. [Troubleshooting](#12-troubleshooting)
13. [API reference (platform)](#13-api-reference-platform)

---

## 1. Quick start

### Desktop app (recommended for live devices)

```bash
npm run install:all
DROIDLENS_MOCK=false npm run dev:electron
```

Or install the AppImage / `.deb` / `.exe` / `.dmg` from [GitHub Releases](https://github.com/kiranckumar2210/DroidLens/releases).

### Web / dev mode

```bash
npm run install:all
DROIDLENS_MOCK=false npm run dev
```

Open **http://127.0.0.1:5173** (frontend) — the backend runs on **http://127.0.0.1:8765**.

### Three ways to inspect

| Mode | Device required? | Best for |
|------|------------------|----------|
| **Connect Live Device** | Yes (or cloud) | Real-time hierarchy + screenshot |
| **Open XML Package** | No | Saved dumps, CI fixtures, sharing with QA |
| **Open Sample Project** | No | Learning the UI without setup |

---

## 2. Dashboard overview

On the Dashboard you choose a **platform pill** before connecting:

- **Android** — USB/Wi‑Fi device via ADB
- **iOS** — Simulator or physical device (macOS + WDA)
- **HarmonyOS** — Device via HDC

Each live card shows toolchain status (e.g. “ADB ready”, “iOS ready”, device count) and a refresh button.

### Live connect flow

1. Expand **Connect Live Device**
2. Select **Platform**
3. Pick a device from the dropdown (refresh if empty)
4. Optionally enter **Package** (Android/HarmonyOS) or **Bundle ID** (iOS)
5. Click **Start … Inspection**

### Check toolchain from the API

```bash
curl -s http://127.0.0.1:8765/platform/status | python3 -m json.tool
```

Response includes availability for `android`, `ios`, `harmonyos`, and `cloud`.

---

## 3. Android (live)

### Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Android SDK platform-tools** | `adb` on PATH |
| **USB debugging** | Enabled on the device |
| **Developer options** | Unlocked on the phone |

Install platform-tools:

```bash
# Ubuntu / Debian
sudo apt install android-sdk-platform-tools

# macOS (Homebrew)
brew install android-platform-tools

# Or download from Google:
# https://developer.android.com/studio/releases/platform-tools
```

Verify:

```bash
adb devices
# Expected: device serial with state "device"
```

### Connect via USB

1. Plug in the phone and accept the **USB debugging** prompt
2. Dashboard → **Android** → select your serial → **Start Android Inspection**

### Connect via Wi‑Fi

From the inspector toolbar (or API):

```bash
curl -X POST http://127.0.0.1:8765/adb/connect-wifi \
  -H 'Content-Type: application/json' \
  -d '{"host":"192.168.1.42","port":5555}'
```

On the device, enable **Wireless debugging** (Android 11+) or `adb tcpip 5555` (older).

### Optional: filter by app package

Enter `com.example.app` in the **Package** field before connect. DroidLens stores this on the session for code export context; launch is available via the API (`POST /app/launch`).

### What DroidLens captures

- **UI hierarchy** — `uiautomator dump` XML (`<hierarchy>`)
- **Screenshot** — `adb exec-out screencap -p`
- **Coordinate mapping** — aligns tap targets on screenshot vs hierarchy bounds

### Android-specific locators

Resource ID, UiAutomator2, XPath, content-desc, text, bounds, and composite strategies. See [Locators by platform](#10-locators-by-platform).

### Android troubleshooting

| Problem | Fix |
|---------|-----|
| No devices in list | Run `adb devices`; accept authorization prompt |
| `unauthorized` | Revoke USB debugging authorizations on phone, reconnect |
| `offline` | Replug cable; `adb kill-server && adb start-server` |
| Empty UI dump | Open an app on screen; retry refresh |
| Wrong element on tap | Use manual refresh; disable live refresh during recording |

Custom ADB path:

```bash
export DROIDLENS_ADB=/path/to/adb
```

---

## 4. iOS (live)

iOS live inspection requires **macOS** for Simulator support. Physical devices need **WebDriverAgent (WDA)** for the accessibility hierarchy.

### Prerequisites summary

| Setup | Hierarchy source | Screenshot source |
|-------|------------------|-------------------|
| **Simulator** | WebDriverAgent (recommended) or simctl + WDA | WDA or `simctl io screenshot` |
| **Physical device** | WebDriverAgent | WDA or `idevicescreenshot` |

Tools:

- **Xcode** + Command Line Tools (`xcrun simctl`)
- **WebDriverAgent** on port **8100** (Appium or standalone)
- **libimobiledevice** (optional, physical): `idevice_id`, `idevice_ui`, `idevicescreenshot`

```bash
# macOS — libimobiledevice
brew install libimobiledevice
```

### Option A — iOS Simulator (recommended path)

#### Step 1: Boot a simulator

```bash
# List available simulators
xcrun simctl list devices available

# Boot one (use UDID from list)
xcrun simctl boot <UDID>
open -a Simulator
```

Or boot from **Xcode → Open Developer Tool → Simulator**.

#### Step 2: Start WebDriverAgent

WDA exposes HTTP endpoints DroidLens uses:

- `GET /source` — XCUI XML page source
- `GET /screenshot` — PNG (base64)

**Via Appium 2:**

```bash
npm install -g appium
appium driver install xcuitest
appium
# In another terminal, start a session with your desired caps, or use Appium Inspector
```

**Standalone WDA** (Xcode):

1. Clone [WebDriverAgent](https://github.com/appium/WebDriverAgent)
2. Open `WebDriverAgent.xcodeproj` in Xcode
3. Select your Simulator as destination
4. Run the **WebDriverAgentRunner** test target
5. WDA listens on `http://127.0.0.1:8100` by default

Verify WDA:

```bash
curl -s http://127.0.0.1:8100/status
curl -s http://127.0.0.1:8100/source | head -c 200
```

#### Step 3: Connect in DroidLens

1. Dashboard → **iOS**
2. Select the Simulator UDID (name shown in dropdown)
3. Optionally enter **Bundle ID** (e.g. `com.apple.Preferences`)
4. **Start iOS Inspection**

DroidLens auto-boots the simulator if it is not already running.

#### WDA URL override

If WDA runs on a non-default host/port:

```bash
export DROIDLENS_WDA_URL=http://127.0.0.1:8100
```

Restart the DroidLens backend after changing env vars.

### Option B — Physical iPhone / iPad

1. Connect device via USB; trust the computer on the device
2. Verify: `idevice_id -l`
3. Start **WebDriverAgent** signed with your Apple Developer team (required for iOS 17+)
4. Dashboard → **iOS** → select the device UDID → connect

Without WDA, hierarchy capture falls back to `idevice_ui dump` when available; WDA is strongly recommended for consistent XCUI XML.

### iOS XML format

Page source uses **XCUIElementType** nodes, for example:

```xml
<XCUIElementTypeApplication name="MyApp" x="0" y="0" width="390" height="844">
  <XCUIElementTypeButton name="login" label="Login" x="20" y="340" width="350" height="50"/>
</XCUIElementTypeApplication>
```

### iOS-specific locators

Accessibility ID (`name`), iOS Predicate, iOS Class Chain, XPath, label, coordinate. Generated automatically in the Locator panel.

### iOS troubleshooting

| Problem | Fix |
|---------|-----|
| “iOS unavailable” on Linux | iOS live requires macOS; use **Offline XML** or **Sample iOS** mock |
| No simulators listed | Install Xcode; run `xcrun simctl list` |
| “WebDriverAgent required” | Start WDA; confirm `curl http://127.0.0.1:8100/status` |
| Empty hierarchy | Open an app in Simulator; ensure WDA session is active |
| Physical device not listed | Install libimobiledevice; check cable/trust prompt |

---

## 5. HarmonyOS (live)

HarmonyOS inspection uses Huawei’s **HDC** (Harmony Device Connector), similar to ADB for Android.

### Prerequisites

| Requirement | Notes |
|-------------|--------|
| **HDC** | HarmonyOS SDK / DevEco toolchain on PATH |
| **Device** | USB debugging / developer mode enabled |
| **uitest** | Available on device for layout dump |

Verify:

```bash
hdc list targets
# Expected: device ID(s), not "[Empty]"
```

Install HDC via [HarmonyOS DevEco Studio](https://developer.huawei.com/consumer/en/deveco-studio/) and add the SDK `toolchains` directory to your PATH.

### Connect

1. Dashboard → **HarmonyOS**
2. Select device from dropdown
3. Optionally enter **Package** / bundle name
4. **Start HarmonyOS Inspection**

### What DroidLens captures

- **UI hierarchy** — `hdc shell uitest dumpLayout`
- **Screenshot** — `hdc shell snapshot_display` pulled via `hdc file recv`

### HarmonyOS locators

Resource ID, text, XPath, accessibility-id, class name, bounds (where present in dump XML).

### HarmonyOS troubleshooting

| Problem | Fix |
|---------|-----|
| `hdc not found` | Add DevEco SDK toolchains to PATH |
| Empty device list | `hdc list targets`; reconnect USB |
| Dump failed | Ensure `uitest` service on device; unlock screen |
| Linux vs Windows | Use HDC build matching your OS from Huawei SDK |

---

## 6. Cloud device farm (Appium)

Use **BrowserStack**, **Sauce Labs**, **LambdaTest**, or any **Appium 2**-compatible hub when you do not have local devices.

### Configure environment

Set these **before starting** the DroidLens backend:

```bash
# Appium 2 hub URL (examples)
export DROIDLENS_APPIUM_URL="https://hub.browserstack.com/wd/hub"
# export DROIDLENS_APPIUM_URL="https://ondemand.us-west-1.saucelabs.com:443/wd/hub"

# W3C capabilities (alwaysMatch format is wrapped internally)
export DROIDLENS_APPIUM_CAPABILITIES='{
  "platformName": "Android",
  "appium:deviceName": "Samsung Galaxy S23",
  "appium:platformVersion": "13.0",
  "appium:app": "bs://your-app-id",
  "bstack:options": {
    "userName": "YOUR_USER",
    "accessKey": "YOUR_KEY"
  }
}'
```

For **iOS cloud**, set `"platformName": "iOS"` and iOS-specific caps (device name, app, etc.).

Restart backend:

```bash
DROIDLENS_MOCK=false npm run dev
```

### Connect in the UI

1. When cloud is configured, a **Cloud — …** device appears in the **Android** device list (after refresh)
2. Select it and start live inspection
3. DroidLens creates an Appium session, pulls `/source` and `/screenshot`, and maps coordinates like a local device

### BrowserStack example (Android)

```bash
export DROIDLENS_APPIUM_URL="https://hub.browserstack.com/wd/hub"
export DROIDLENS_APPIUM_CAPABILITIES='{
  "platformName": "Android",
  "appium:deviceName": "Google Pixel 7",
  "appium:platformVersion": "13.0",
  "appium:app": "bs://<app-id-from-browserstack-upload>",
  "bstack:options": {
    "userName": "your_username",
    "accessKey": "your_access_key",
    "projectName": "DroidLens",
    "buildName": "inspect-build-1",
    "sessionName": "UI inspection"
  }
}'
```

### Sauce Labs example (iOS)

```bash
export DROIDLENS_APPIUM_URL="https://ondemand.us-west-1.saucelabs.com:443/wd/hub"
export DROIDLENS_APPIUM_CAPABILITIES='{
  "platformName": "iOS",
  "appium:deviceName": "iPhone 14",
  "appium:platformVersion": "16.2",
  "appium:app": "storage:your-app.zip",
  "sauce:options": {
    "username": "your_user",
    "accessKey": "your_key"
  }
}'
```

### Cloud troubleshooting

| Problem | Fix |
|---------|-----|
| Cloud device not listed | Check env vars; restart backend; `GET /platform/status` → `cloud.available` |
| Session creation failed | Validate caps JSON; check hub credentials |
| Empty page source | Wait for app to launch; increase hub session timeout |
| Wrong platform locators | Set `platformName` correctly in capabilities |

---

## 7. Offline XML packages

Works on **all platforms** without a device — same workflow as UIAutomatorViewer.

### File pairing

DroidLens auto-pairs files by basename:

```
Login.xml  +  Login.png   →  one package "Login"
Home.xml   +  Home.png    →  one package "Home"
```

Supported XML sources:

| Platform | Typical XML root |
|----------|------------------|
| Android | `<hierarchy>` from `uiautomator dump` |
| iOS | `<XCUIElementTypeApplication>` from WDA / Appium |
| HarmonyOS | Layout dump from `uitest dumpLayout` |

### How to open

1. **Dashboard → Open XML Package** → import dialog, or
2. **Drag and drop** `.xml` + `.png` onto the Dashboard, or
3. **Recent Sessions** → re-open a previous file path (Electron desktop)

### Export from a live session

In the inspector, use **Export XML Package** to save the current hierarchy + screenshot as a paired dump for sharing or offline tools.

### Offline tools (Dashboard → Offline Tools)

| Tool | Purpose |
|------|---------|
| **Compare XML Dumps** | Diff two hierarchy files across builds |
| **Locator Health Scan** | Score locators against one XML file |
| **Validate Locator Suite** | CI-style validation of `locators.json` |
| **Locator Migration** | Map broken locators from old XML to new XML |

CLI equivalents: see [`docs/CLI.md`](CLI.md).

---

## 8. Sample / mock projects

No device or toolchain required.

1. Dashboard → **Open Sample Project**
2. Choose platform pill: **Android**, **iOS**, or **HarmonyOS**
3. Click **Load … Sample**

Each mock session includes realistic hierarchy XML and a generated screenshot so you can explore locators, code export, and the inspector UI.

API:

```bash
curl -X POST 'http://127.0.0.1:8765/session/mock?platform=ios'
curl -X POST 'http://127.0.0.1:8765/session/mock?platform=harmonyos'
curl -X POST 'http://127.0.0.1:8765/session/mock?platform=android'
```

---

## 9. Inspector workflow (all platforms)

After connect (live, offline, or mock):

| Action | Shortcut / control |
|--------|-------------------|
| Select element | Click on screenshot |
| Live refresh | Toggle in toolbar (live sessions only) |
| Manual refresh | Refresh button |
| Locator details | Inspector → Locators tab |
| Code export | Generate code / Page Object |
| Save to repository | Save modal (premium) |
| XML diff / health | Dashboard → Offline Tools |

**Live refresh** uses WebSocket (`/ws/live`) and sends `platform` with each subscribe so the backend uses the correct adapter.

### Session history

Dashboard → **Recent Sessions** stores:

- Live: device ID + platform + package
- Offline: file paths (Electron)
- Mock: sample project entries

---

## 10. Locators by platform

| Locator type | Android | iOS | HarmonyOS |
|--------------|:-------:|:---:|:---------:|
| Resource ID | ✓ | — | ✓ |
| Accessibility ID | ✓ | ✓ | ✓ |
| Text / label | ✓ | ✓ | ✓ |
| Content-desc | ✓ | — | ✓ |
| UiAutomator2 | ✓ | — | — |
| iOS Predicate | — | ✓ | — |
| iOS Class Chain | — | ✓ | — |
| XPath | ✓ | ✓ | ✓ |
| Coordinate | ✓ | ✓ | ✓ |
| Bounds | ✓ | ✓ | ✓ |

DroidLens ranks locators by stability and uniqueness; the recommended locator is marked in the UI.

### Code export profiles

Default profile is **Python + UiAutomator2** (Android-focused). For iOS automation, prefer exported **accessibility id**, **predicate**, or **class chain** values in your Appium / XCUITest project.

---

## 11. Environment variables

| Variable | Platform | Description | Default |
|----------|----------|-------------|---------|
| `DROIDLENS_MOCK` | All | `true` disables real device adapters in some dev setups | `false` |
| `DROIDLENS_ADB` | Android | Path to `adb` | PATH |
| `DROIDLENS_WDA_URL` | iOS | WebDriverAgent base URL | `http://127.0.0.1:8100` |
| `DROIDLENS_APPIUM_URL` | Cloud | Appium 2 hub URL | *(unset)* |
| `DROIDLENS_APPIUM_CAPABILITIES` | Cloud | JSON capabilities object | `{}` |
| `DROIDLENS_PORT` | All | Backend API port | `8765` |
| `DROIDLENS_DEBUG_SCREENSHOT` | All | Save screenshots to disk when `1` | off |
| `DROIDLENS_DEBUG_DIR` | All | Debug screenshot directory | `/tmp/droidlens-screenshots` |

Set variables in your shell, `.env`, or Electron launch script before starting the backend.

---

## 12. Troubleshooting

### General

```bash
# Health check
curl http://127.0.0.1:8765/health

# Platform toolchain status
curl http://127.0.0.1:8765/platform/status

# List devices per platform
curl 'http://127.0.0.1:8765/devices?platform=android&refresh=true'
curl 'http://127.0.0.1:8765/devices?platform=ios'
curl 'http://127.0.0.1:8765/devices?platform=harmonyos'
```

### Port already in use

```bash
bash scripts/ensure-backend-port.sh
# Or use another port:
DROIDLENS_PORT=8766 npm run dev
```

### Live connect returns 503

- Read the error message in the Dashboard alert
- Usually: device not found, unauthorized (Android), or missing WDA (iOS Simulator)
- Confirm `DROIDLENS_MOCK=false` when using real devices

### WebSocket live refresh fails (403)

In dev mode, live refresh connects directly to `ws://127.0.0.1:8765/ws/live`. Ensure the backend is running and no proxy strips WebSocket paths.

### Platform not available on your OS

| Platform | Linux | macOS | Windows |
|----------|:-----:|:-----:|:-------:|
| Android | ✓ | ✓ | ✓ |
| iOS live | mock/offline only | ✓ | mock/offline only |
| HarmonyOS | ✓* | ✓* | ✓* |
| Cloud | ✓ | ✓ | ✓ |

\* Requires HDC toolchain installed for that OS.

---

## 13. API reference (platform)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/platform/status` | Toolchain availability per platform |
| `GET` | `/devices?platform=android\|ios\|harmonyos&refresh=true` | List devices |
| `POST` | `/session/connect` | Body: `{ "device_id", "platform", "package"? }` |
| `POST` | `/session/refresh` | Same body; refresh live session |
| `POST` | `/session/mock?platform=android\|ios\|harmonyos` | Load sample session |
| `POST` | `/session/offline` | Upload XML / screenshot (JSON body) |
| `POST` | `/app/launch` | Body: `{ "device_id", "platform", "package", "activity"? }` |
| `WS` | `/ws/live` | Subscribe: `{ "action":"subscribe", "device_id", "platform", "interval" }` |

### Example: connect Android

```bash
curl -X POST http://127.0.0.1:8765/session/connect \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -d '{"device_id":"emulator-5554","platform":"android","package":"com.example.app"}'
```

### Example: connect iOS Simulator

```bash
curl -X POST http://127.0.0.1:8765/session/connect \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -d '{"device_id":"YOUR-SIMULATOR-UDID","platform":"ios"}'
```

---

## Related docs

- [`docs/CLI.md`](CLI.md) — CI validation without a device
- [`docs/architecture.md`](architecture.md) — system design
- [`docs/DEPLOY-ELECTRON.md`](DEPLOY-ELECTRON.md) — desktop + cloud auth
- [`docs/roadmap.md`](roadmap.md) — upcoming platform features

---

**Need help?** Open an issue on [GitHub](https://github.com/kiranckumar2210/DroidLens/issues) with your platform, OS, toolchain versions (`adb --version`, `xcrun simctl list`, `hdc -v`), and the output of `/platform/status`.
