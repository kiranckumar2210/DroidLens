# DroidLens Screenshots

Add marketing and documentation images here before publishing the repository.

## Recommended captures

| File | Suggested content |
|------|-------------------|
| `dashboard.png` | Main dashboard with device list and inspection entry cards |
| `live-inspector.png` | Live session with screenshot, element tree, and highlight |
| `locator-engine.png` | Locator panel with ranked strategies and scores |
| `recording-studio.png` | Three-pane Recording Studio (screenshot · timeline · code) |
| `code-generator.png` | Generated uiautomator2 / Appium script output |
| `admin-panel.png` | Admin dashboard or System Settings page |
| `demo.gif` | 15–30 s walkthrough: connect → inspect → locate → export |

## Guidelines

- **Resolution:** 1920×1080 or 1440×900 (16:9 or similar)
- **Theme:** Capture both light and dark mode if possible; default to dark for consistency
- **Privacy:** Blur or use emulators with sample apps — no real user data
- **Format:** PNG for stills, GIF or WebM for animations
- **Size:** Optimize GIFs to under ~5 MB for GitHub README loading

## Capture tips

```bash
# Run the app locally
DROIDLENS_MOCK=true npm run dev
# or
npm run dev:electron
```

Use your OS screenshot tool or a screen recorder (OBS, Peek on Linux, etc.).

After adding files, verify they render in the root [`README.md`](../../README.md).
