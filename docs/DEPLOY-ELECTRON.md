# DroidLens Desktop — Electron + GitHub Releases

Use the **desktop app** for live Android device inspection (local ADB).  
Use **Railway** for hosted accounts, admin, and web access.

**Repository:** https://github.com/kiranckumar2210/DroidLens

---

## Architecture (hybrid mode)

```text
┌─────────────────────────────────────────────────────────┐
│  DroidLens Desktop (Electron on your laptop)            │
│  ┌──────────────┐         ┌──────────────────────────┐  │
│  │ React UI     │ login   │ Railway cloud API        │  │
│  │              │────────►│ /login /profile /admin   │  │
│  └──────┬───────┘         └──────────────────────────┘  │
│         │ devices / ADB                                   │
│         ▼                                                 │
│  ┌──────────────┐         ┌──────────────────────────┐  │
│  │ Local Python │◄──USB──►│ Your Android phone       │  │
│  │ backend :8765│         └──────────────────────────┘  │
│  └──────────────┘                                         │
└─────────────────────────────────────────────────────────┘
```

| Traffic | Goes to |
|---------|---------|
| Login, register, profile, payments, admin | **Cloud** (Railway URL) |
| Devices, ADB, inspect, record, codegen | **Local** (`127.0.0.1:8765`) |

---

## Part 1 — Prerequisites

| Requirement | Notes |
|-------------|-------|
| Node.js 18+ | `node -v` |
| Python 3.10+ | `python3 --version` |
| Android platform-tools | `adb devices` works |
| Railway app deployed | Your cloud URL + JWT secret |

---

## Part 2 — Hybrid desktop (cloud login + local devices)

### Step 1 — Copy JWT secret from Railway

Railway → **Variables** → copy `DROIDLENS_JWT_SECRET`.

For hybrid desktop login, also set CORS so the Electron UI (origin `http://127.0.0.1:8765`) can call the cloud API:

```env
DROIDLENS_CORS_ORIGINS=https://YOUR-APP.up.railway.app,http://127.0.0.1:8765,http://localhost:8765
```

Local desktop **must use the same value** so local backend accepts cloud login tokens.

### Step 2 — Create `.env.desktop`

```bash
cp .env.desktop.example .env.desktop
```

Edit `.env.desktop`:

```env
DROIDLENS_CLOUD_API_URL=https://YOUR-APP.up.railway.app
DROIDLENS_JWT_SECRET=same-secret-as-railway
DROIDLENS_MOCK=false
```

### Step 3 — Install dependencies

```bash
bash scripts/install-all.sh
cd backend && python3 -m pip install -r requirements.txt
```

### Step 4 — Launch hybrid desktop

```bash
chmod +x scripts/run-desktop-cloud.sh
bash scripts/run-desktop-cloud.sh
```

Or manually:

```bash
export DROIDLENS_CLOUD_API_URL=https://YOUR-APP.up.railway.app
export DROIDLENS_JWT_SECRET=your-railway-jwt-secret
export DROIDLENS_MOCK=false
npm run dev:electron
```

### Step 5 — Verify

1. **Sign in** with your Railway account  
2. Run `adb devices` — phone should appear  
3. DroidLens dashboard → **Connect Live Device** → your device listed  
4. Cloud health: `curl https://YOUR-APP.up.railway.app/health`  
5. Local health: `curl http://127.0.0.1:8765/health` → `"mock_mode": false`

### Packaged app config (optional)

Create `electron/desktop-config.json`:

```json
{
  "cloudApiUrl": "https://YOUR-APP.up.railway.app"
}
```

Set `DROIDLENS_JWT_SECRET` in the environment before launching the installed app.

---

## Part 3 — Local-only desktop (no cloud)

All auth and devices run locally — no Railway needed.

```bash
DROIDLENS_MOCK=false npm run dev:electron
```

Register a local account. Good for offline development.

---

## Part 4 — Build installers

### Build on your machine

```bash
bash scripts/install-all.sh
npm run build:electron
```

Output: `dist-electron/`

The DroidLens icon appears in the Linux app menu, Windows taskbar, and macOS dock. Regenerate assets with `npm run generate:icons` before building.

To pin a Linux AppImage to your application menu after building:

```bash
./scripts/install-linux-desktop-entry.sh --exec ./dist-electron/DroidLens-1.0.0.AppImage
```

Full go-to-market steps: **[RELEASE-TO-MARKET.md](./RELEASE-TO-MARKET.md)**.

| Platform | Artifact |
|----------|----------|
| Linux | `*.AppImage`, `*.deb` |
| Windows | `*.exe` (build on Windows) |
| macOS | `*.dmg` (build on macOS) |

### Requirements for packaged backend

Users need **Python 3.10+** and `pip install -r backend/requirements.txt` unless you bundle Python (future improvement).

---

## Part 5 — Publish to GitHub Releases

### Option A — Manual upload

1. Build: `npm run build:electron`
2. GitHub → **Releases** → **Draft a new release**
3. Tag: `v1.0.0`
4. Upload files from `dist-electron/`
5. Publish release

### Option B — GitHub Actions (Linux AppImage)

Push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Workflow `.github/workflows/release-desktop.yml` builds and attaches Linux artifacts automatically.

---

## Part 6 — User install guide (share with team)

1. Download **DroidLens** from [GitHub Releases](https://github.com/kiranckumar2210/DroidLens/releases)  
2. Install [Android platform-tools](https://developer.android.com/tools/releases/platform-tools)  
3. Enable **USB debugging** on phone  
4. Run `adb devices` and authorize the PC  
5. Create `desktop-config.json` (see Part 2) with your cloud URL  
6. Set `DROIDLENS_JWT_SECRET` to match server  
7. Launch DroidLens Desktop → Sign in → Connect device  

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Login works, devices empty | `DROIDLENS_MOCK=false`; check `adb devices` |
| Login fails on desktop | Check `DROIDLENS_CLOUD_API_URL`; Railway app running |
| 401 on live inspect after login | `DROIDLENS_JWT_SECRET` must match Railway |
| Admin opens web not cloud | Admin always uses cloud URL when hybrid configured |
| "Failed to fetch" on login | Packaged app must load UI from `http://127.0.0.1:8765` (not `file://`). Rebuild after fixes. |
| CORS errors on cloud login | Railway `DROIDLENS_CORS_ORIGINS` must include `http://127.0.0.1:8765,http://localhost:8765` plus your Railway URL. Wildcard `*` disables credentialed CORS (Bearer auth still works). |

---

## Quick reference

```bash
# Hybrid (recommended)
bash scripts/run-desktop-cloud.sh

# Build release
npm run build:electron

# Tag release
git tag v1.0.0 && git push origin v1.0.0
```
