# Deploy DroidLens on Railway

Deploy the full DroidLens web app (React UI + FastAPI API + auth) from GitHub in ~15 minutes.

**Repository:** https://github.com/kiranckumar2210/DroidLens

---

## What you get

| URL | Serves |
|-----|--------|
| `https://your-app.up.railway.app/` | DroidLens web UI |
| `https://your-app.up.railway.app/health` | Health check |
| `https://your-app.up.railway.app/docs` | API documentation |
| `https://your-app.up.railway.app/admin` | Admin console (after login) |

**Note:** Live Android device inspection requires ADB on the user's machine. The Railway deployment runs in **mock mode** (`DROIDLENS_MOCK=true`) — perfect for guest/mock/XML tools, user accounts, trials, and payments. Ship the **Electron desktop app** separately for real device users.

---

## Step 1 — Create a Railway project

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select **`kiranckumar2210/DroidLens`**.
4. Railway detects `Dockerfile` and `railway.toml` automatically.

---

## Step 2 — Add a persistent volume (required for user accounts)

Without a volume, user accounts and payments are lost on every redeploy.

1. In your Railway service, open **Settings** → **Volumes**.
2. Click **Add Volume**.
3. Mount path: `/data`
4. Size: **1 GB** (enough to start)

---

## Step 3 — Set environment variables

Open **Variables** and add:

### Required

| Variable | Value | Notes |
|----------|-------|-------|
| `DROIDLENS_AUTH_DB` | `/data/auth.db` | Persists users, licenses, payments |
| `DROIDLENS_JWT_SECRET` | *(64-char random)* | `openssl rand -hex 32` |
| `DROIDLENS_LICENSE_CACHE_SECRET` | *(64-char random)* | `openssl rand -hex 32` |
| `DROIDLENS_ADMIN_EMAIL` | `info.kiranc@gmail.com` | First register → admin role |
| `DROIDLENS_PUBLIC_URL` | `https://YOUR-APP.up.railway.app` | Set after Step 4 |

### Recommended for production

| Variable | Value |
|----------|-------|
| `DROIDLENS_MOCK` | `true` |
| `DROIDLENS_PAYMENT_PROVIDER` | `mock` or `phonepe` |
| `DROIDLENS_LIFETIME_PRICE_INR` | `199` |
| `DROIDLENS_TRIAL_DAYS` | `7` |

### PhonePe (when ready for real payments)

| Variable | Value |
|----------|-------|
| `DROIDLENS_PAYMENT_PROVIDER` | `phonepe` |
| `PHONEPE_ENVIRONMENT` | `production` |
| `PHONEPE_MERCHANT_ID` | from PhonePe dashboard |
| `PHONEPE_CLIENT_ID` | from PhonePe dashboard |
| `PHONEPE_CLIENT_SECRET` | from PhonePe dashboard |
| `PHONEPE_CALLBACK_URL` | `https://YOUR-APP.up.railway.app/?payment_return=1` |
| `PHONEPE_WEBHOOK_USERNAME` | webhook auth user |
| `PHONEPE_WEBHOOK_SECRET` | webhook auth password |

Railway injects `PORT` automatically — do not set it manually.

---

## Step 4 — Generate a public domain

1. Open **Settings** → **Networking** → **Generate Domain**.
2. Copy the URL (e.g. `https://droidlens-production.up.railway.app`).
3. Update `DROIDLENS_PUBLIC_URL` to match.
4. Redeploy if needed (**Deployments** → **Redeploy**).

---

## Step 5 — Custom domain (optional)

1. **Settings** → **Networking** → **Custom Domain**.
2. Add e.g. `app.droidlens.com`.
3. Create a CNAME pointing to Railway's target.
4. Update `DROIDLENS_PUBLIC_URL` to your custom domain.

---

## Step 6 — First deploy & admin setup

1. Wait for the deploy to finish (green checkmark).
2. Open your Railway URL in a browser.
3. **Register** with the email set in `DROIDLENS_ADMIN_EMAIL`.
4. Go to **`/admin/settings`**:
   - Turn **Enable Subscription System** → **ON** (for production billing)
   - Configure trial days, lifetime price, PhonePe toggle
5. Test login/logout with a second account.

---

## Step 7 — Enable auto-deploy from GitHub

Railway redeploys automatically on every push to your connected branch (usually `main`).

To deploy manually: **Deployments** → **Redeploy**.

---

## Scaling as users grow

| Stage | Railway action |
|-------|----------------|
| **Launch (0–500 users)** | 1 replica, 1 GB volume, default plan |
| **Growth (500–5k)** | Upgrade Railway plan, increase replicas in **Settings → Deploy** |
| **High traffic (5k+)** | Migrate auth DB to PostgreSQL (future), add Redis, use CDN for static assets |

JWT auth is stateless — adding replicas scales login traffic. All replicas must share the same `/data` volume (or external DB).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Deploy fails at frontend build | Check Railway build logs; ensure `frontend/package.json` is committed |
| Users lost after redeploy | Add volume + set `DROIDLENS_AUTH_DB=/data/auth.db` |
| Health check failing | Open `/health` in browser; check deploy logs for Python errors |
| WebSocket errors | Should work on same Railway domain (wss:// auto-detected) |
| PhonePe redirect fails | `DROIDLENS_PUBLIC_URL` and `PHONEPE_CALLBACK_URL` must match live URL |
| Admin role not assigned | Register with exact email in `DROIDLENS_ADMIN_EMAIL` |

---

## Local Docker test (optional)

```bash
docker build -t droidlens .
docker run -p 8765:8765 \
  -e PORT=8765 \
  -e DROIDLENS_JWT_SECRET=dev-secret-change-me \
  -e DROIDLENS_LICENSE_CACHE_SECRET=dev-cache-secret \
  -e DROIDLENS_ADMIN_EMAIL=admin@test.com \
  -e DROIDLENS_PUBLIC_URL=http://localhost:8765 \
  droidlens
```

Open http://localhost:8765

---

## Desktop app for live devices

Railway hosts the **web + auth + billing** layer. For real Android ADB:

```bash
npm run build:electron
```

Upload installers from `dist-electron/` to [GitHub Releases](https://github.com/kiranckumar2210/DroidLens/releases).
