# Changelog

All notable changes to **DroidLens** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-07-04

### Added

- **Live Inspector** — real-time UIAutomator dump, screenshot sync, element hierarchy
- **Offline Inspector** — XML and screenshot upload workflow
- **Mock Inspector** — bundled sample UI for demos and CI
- **Locator Intelligence Engine** — ranked locators (resource-id, XPath, UiSelector, relative)
- **Custom Locator Builder** — visual rules with live validation
- **Code Generator** — Python uiautomator2, Appium multi-language, Page Object Model
- **Recording Studio** — IDE-style three-pane recorder with Monaco editor and timeline
- **Device Manager** — USB/WiFi ADB, device info, multi-device support
- **Authentication** — registration, login, JWT sessions, trial and lifetime licensing
- **Admin Console** — dashboard, users, payments, subscriptions, activity logs
- **System Settings** — admin-controlled subscription, payment, trial, guest, and feature flags
- **PhonePe payment integration** — lifetime license purchase flow
- **Electron desktop app** — Linux, macOS, and Windows builds
- **WebSocket support** — live session updates
- **Brand assets** — logo, icon set, and color palette

### Changed

- Rebranded from InspectIQ internal module naming to **DroidLens** product identity
- Consolidated auth refresh API to prevent device session / auth token conflicts

### Fixed

- Recording code generation errors during live sessions
- UI dump retry logic for transient ADB failures
- Backend port conflict detection in dev scripts

---

## [Unreleased]

### Planned (v1.1)

- Locator repository export (JSON / CSV / Markdown)
- Session restore and history
- Favorites for locators

### Planned (v2.0)

- iOS adapter
- HarmonyOS adapter
- Cloud device farm integration

---

[1.0.0]: https://github.com/kiranckumar2210/DroidLens/releases/tag/v1.0.0
