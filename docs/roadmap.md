# DroidLens — Implementation Plan & Roadmap

**Product:** DroidLens · **Tagline:** *See. Inspect. Automate.*

## v1.0 – v1.3

See git history — live/offline inspection, locator engine, XML packages, export, diff, health scan, recording POM, CLI validation, migration assistant.

## v2.0 (Current)

- [x] iOS adapter — Simulator (simctl), WebDriverAgent client, idevice tools
- [x] HarmonyOS adapter — HDC uitest dumpLayout + snapshot
- [x] Platform picker on Dashboard (Android / iOS / HarmonyOS)
- [x] Platform-aware connect validation and live refresh
- [x] iOS XCUI parser (`engine/ios_parser.py`)
- [x] Mock sessions per platform (`POST /session/mock?platform=ios`)
- [x] Cloud device farm — Appium 2 remote via `DROIDLENS_APPIUM_URL` + capabilities JSON
- [x] Platform toolchain status API (`GET /platform/status`)

### Cloud device farm setup

See **[docs/PLATFORM-GUIDE.md § Cloud device farm](PLATFORM-GUIDE.md#6-cloud-device-farm-appium)** for BrowserStack, Sauce Labs, and env var examples.

```bash
export DROIDLENS_APPIUM_URL="https://hub.browserstack.com/wd/hub"
export DROIDLENS_APPIUM_CAPABILITIES='{"platformName":"Android","deviceName":"Samsung Galaxy S23","app":"bs://..."}'
```

When configured, a **Cloud — …** device appears in the Android device list.

### iOS live inspection

See **[docs/PLATFORM-GUIDE.md § iOS](PLATFORM-GUIDE.md#4-ios-live)** for full Simulator + WDA setup.

1. Boot an iOS Simulator (macOS + Xcode) or connect a physical device
2. Start WebDriverAgent (Appium or standalone) on port 8100
3. Optionally set `DROIDLENS_WDA_URL=http://127.0.0.1:8100`
4. Select **iOS** on the Dashboard and connect

## v2.1 (Planned)

- [ ] iOS recording + Appium code export profiles
- [ ] HarmonyOS locator strategies polish
- [ ] BrowserStack / Sauce Labs preset capability templates in UI
