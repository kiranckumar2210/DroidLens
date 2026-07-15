# Release DroidLens to Customers

Step-by-step guide to ship DroidLens Desktop to users, teams, or the public market.

**Repository:** https://github.com/kiranckumar2210/DroidLens  
**Cloud backend:** Railway (accounts, admin, billing)  
**Desktop app:** Electron (local ADB + UI)

---

## Overview

| Layer | What you ship | Where it runs |
|-------|---------------|---------------|
| **Cloud API** | Auth, profiles, admin, payments | Railway |
| **Desktop app** | AppImage / `.deb` / `.exe` / `.dmg` | User's laptop |
| **Branding** | App icon, name, version | Built into installers |

Customers download the **desktop installer**, sign in against your **cloud URL**, and connect phones via **USB + ADB** locally.

---

## Phase 1 — Prepare branding & icon

The app icon is generated from the DroidLens mark (Android + magnifying glass).

### Step 1.1 — Generate icon files

```bash
cd /path/to/DroidLens
bash scripts/install-all.sh
npm run generate:icons
```

This creates:

| File | Purpose |
|------|---------|
| `assets/branding/icon.png` | Master 512×512 (macOS, window icon) |
| `assets/branding/icon.ico` | Windows installer |
| `assets/branding/icons/256x256.png` | Linux menu / dock icon |
| `assets/branding/icons/*.png` | All platform sizes |

### Step 1.2 — Verify icon in dev

```bash
npm run dev:electron
```

You should see the DroidLens icon in the window title bar and taskbar.

### Step 1.3 — Commit icons (recommended)

Commit generated PNG/ICO so CI builds match your local branding:

```bash
git add assets/branding/icon.png assets/branding/icon.ico assets/branding/icons/
git commit -m "chore: add DroidLens desktop icon assets"
```

---

## Phase 2 — Prepare cloud backend (Railway)

Every customer signs in against your hosted API.

### Step 2.1 — Deploy Railway

Follow [DEPLOY-RAILWAY.md](./DEPLOY-RAILWAY.md). Minimum variables:

```env
DROIDLENS_JWT_SECRET=<long-random-secret>
DROIDLENS_AUTH_DB=/data/auth.db
DROIDLENS_PUBLIC_URL=https://YOUR-APP.up.railway.app
DROIDLENS_CORS_ORIGINS=https://YOUR-APP.up.railway.app,http://127.0.0.1:8765,http://localhost:8765
```

Attach a **Volume** at `/data` so user accounts persist.

### Step 2.2 — Smoke-test cloud

```bash
curl https://YOUR-APP.up.railway.app/health
```

Expect `"status": "ok"`.

### Step 2.3 — Create admin account

1. Register via the web UI or API  
2. Promote yourself to admin in Railway shell / DB if needed  
3. Open `/admin` — confirm dashboard loads  

### Step 2.4 — Configure licensing (optional)

In **Admin → System Settings**:

- **Subscription OFF** (default) — all registered users get full access  
- **Subscription ON** — enable trials, payments, premium gates  

---

## Phase 3 — Build desktop installers

### Step 3.1 — Set cloud URL for packaged app

Edit `electron/desktop-config.json`:

```json
{
  "cloudApiUrl": "https://YOUR-APP.up.railway.app"
}
```

This URL is baked into the desktop build for login/profile calls.

### Step 3.2 — Bump version

In root `package.json`:

```json
"version": "1.0.0"
```

Use [semver](https://semver.org): `1.0.1` for patches, `1.1.0` for features, `2.0.0` for breaking changes.

### Step 3.3 — Build

```bash
npm run build:electron
```

Output in `dist-electron/`:

| Platform | Build on | Artifact |
|----------|----------|----------|
| Linux | Linux | `DroidLens-x.y.z.AppImage`, `DroidLens_x.y.z_amd64.deb` |
| Windows | Windows | `DroidLens Setup x.y.z.exe` |
| macOS | macOS | `DroidLens-x.y.z.dmg` |

Icons are embedded automatically (Linux menu icon, Windows taskbar, macOS dock).

### Step 3.4 — Test the build locally

```bash
export DROIDLENS_JWT_SECRET=<same-as-railway>
./dist-electron/DroidLens-1.0.0.AppImage
```

Checklist:

- [ ] App opens with DroidLens icon in taskbar/dock  
- [ ] Login works (no "Failed to fetch")  
- [ ] `curl http://127.0.0.1:8765/health` returns OK  
- [ ] Phone appears when `adb devices` works  
- [ ] Live inspect connects  

### Step 3.5 — Linux desktop shortcut (optional)

After building, pin to the app menu:

```bash
chmod +x scripts/install-linux-desktop-entry.sh
./scripts/install-linux-desktop-entry.sh --exec ./dist-electron/DroidLens-1.0.0.AppImage
```

---

## Phase 4 — Publish release

### Option A — GitHub Releases (recommended for teams & early customers)

#### Step 4A.1 — Push code

```bash
git push origin main
```

#### Step 4A.2 — Tag version

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions (`.github/workflows/release-desktop.yml`) builds **all platforms** on tag push and attaches installers to the release:

| Platform | Artifacts |
|----------|-----------|
| Linux | `DroidLens-x.y.z.AppImage`, `droidlens_x.y.z_amd64.deb` |
| Windows | `DroidLens Setup x.y.z.exe` |
| macOS | `DroidLens-x.y.z.dmg` (unsigned — users may need to allow in System Settings) |

#### Step 4A.3 — Verify release artifacts

After the workflow completes:

1. GitHub → **Actions** → **Release Desktop** → confirm all three build jobs are green  
2. GitHub → **Releases** → open the tag → confirm Linux, Windows, and macOS installers are attached  
3. Add or edit release notes (features, fixes, known issues) if needed  
4. **Publish release** if it was created as a draft  

#### Step 4A.4 — Share download link

Send customers:

> Download DroidLens: https://github.com/kiranckumar2210/DroidLens/releases/latest

---

### Option B — Direct delivery (enterprise / private beta)

1. Build installers locally  
2. Upload to Google Drive, S3, or your website  
3. Email customers a signed download link  
4. Include the **Customer install guide** below  

---

### Option C — Public app stores (later)

| Store | Notes |
|-------|-------|
| **Microsoft Store** | Requires MSIX packaging, code signing cert (~$200/yr) |
| **Mac App Store** | Apple Developer Program ($99/yr), notarization required |
| **Snap Store** | `snapcraft` config — good for Linux discoverability |
| **Flathub** | Flatpak — wider Linux distribution |

For v1, **GitHub Releases + your website** is the fastest path to market.

---

## Phase 5 — Customer install guide (copy to users)

Send this to every customer:

---

### Install DroidLens Desktop

**Requirements**

- Windows 10+, macOS 11+, or Ubuntu 20.04+  
- Python 3.10+ (`python3 --version`)  
- [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) (`adb`)  
- USB debugging enabled on your Android phone  

**Steps**

1. **Download** the installer for your OS from [Releases](https://github.com/kiranckumar2210/DroidLens/releases/latest)  
   - Linux: `DroidLens-x.y.z.AppImage` or `.deb`  
   - Windows: `DroidLens Setup x.y.z.exe`  
   - macOS: `DroidLens-x.y.z.dmg`  

2. **Install Python dependencies** (one-time):

   ```bash
   pip install -r requirements.txt
   ```

   Or use the copy bundled in the install docs your team provides.

3. **Install ADB** and verify:

   ```bash
   adb devices
   ```

   Authorize your PC on the phone when prompted.

4. **Launch DroidLens**  
   - Linux AppImage: `chmod +x DroidLens*.AppImage && ./DroidLens*.AppImage`  
   - `.deb`: `sudo dpkg -i DroidLens*.deb`  
   - Windows/macOS: run the installer  

5. **Sign in** with the account your admin created (or register if open signup is enabled).

6. **Connect device** → Dashboard → **Connect Live Device** → select your phone.

**Support:** [GitHub Issues](https://github.com/kiranckumar2210/DroidLens/issues)

---

## Phase 6 — Post-release operations

### Version updates

1. Fix / feature on `main`  
2. Bump `version` in `package.json`  
3. Tag `v1.0.1`, push  
4. CI publishes new installers  
5. Notify customers via email / changelog  

### Changelog

Update [CHANGELOG.md](../CHANGELOG.md) for each release:

```markdown
## [1.0.1] - 2026-07-15
### Fixed
- Desktop icon in Linux app menu
- Login CORS for packaged AppImage
```

### Monitoring

- Railway logs for auth/payment errors  
- GitHub Issues for customer bugs  
- Admin dashboard for user counts  

### Security

- Rotate `DROIDLENS_JWT_SECRET` if ever exposed  
- Keep Railway and dependencies updated  
- Never commit `.env.desktop` (contains secrets)  

---

## Quick checklist before go-live

| # | Task | Done |
|---|------|------|
| 1 | Icons generated (`npm run generate:icons`) | ☐ |
| 2 | Railway deployed + volume attached | ☐ |
| 3 | CORS includes desktop origins | ☐ |
| 4 | `desktop-config.json` has production URL | ☐ |
| 5 | `npm run build:electron` succeeds | ☐ |
| 6 | AppImage tested: login + ADB + inspect | ☐ |
| 7 | Git tag pushed → GitHub Release published | ☐ |
| 8 | Customer install guide sent | ☐ |
| 9 | Admin account ready to support users | ☐ |

---

## Related docs

- [DEPLOY-ELECTRON.md](./DEPLOY-ELECTRON.md) — hybrid desktop architecture  
- [DEPLOY-RAILWAY.md](./DEPLOY-RAILWAY.md) — cloud backend  
- [CONTRIBUTING.md](../CONTRIBUTING.md) — development setup  
