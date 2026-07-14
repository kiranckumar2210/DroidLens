# Contributing to DroidLens

Thank you for your interest in contributing to **DroidLens**! This guide covers local setup, workflow, and expectations for pull requests.

---

## Getting Started

### Prerequisites

- Node.js **18+**
- Python **3.10+**
- Git
- Android platform-tools (optional, for live device testing)

### Setup

```bash
git clone https://github.com/kiranckumar2210/DroidLens.git
cd DroidLens
bash scripts/install-all.sh
```

### Run in development

```bash
# Web + API (mock mode)
DROIDLENS_MOCK=true npm run dev

# Desktop
npm run dev:electron
```

- UI: http://localhost:5173
- API docs: http://127.0.0.1:8765/docs

---

## Project Structure

```
droidlens/
├── backend/inspectiq/   # Python FastAPI backend
├── frontend/src/        # React + TypeScript UI
├── electron/            # Desktop shell
├── scripts/             # Dev and install scripts
├── docs/                # Architecture and design docs
└── assets/branding/     # Logos and icons
```

---

## Development Workflow

1. **Fork** the repository and create a feature branch from `main`:

   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make focused changes** — prefer small, reviewable PRs over large rewrites.

3. **Run tests** before submitting:

   ```bash
   cd backend && DROIDLENS_MOCK=true PYTHONPATH=. python3 -m pytest -v
   ```

4. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/):

   ```
   feat: add locator export to CSV
   fix: resolve UI dump retry on Android 14
   docs: update installation guide
   test: cover recording step undo
   refactor: simplify session manager lookup
   ```

5. **Open a Pull Request** with:
   - A clear summary of what changed and why
   - Steps to test manually (if applicable)
   - Screenshots or GIFs for UI changes

---

## Code Guidelines

### Backend (Python)

- Follow existing module layout under `backend/inspectiq/`
- Use type hints and Pydantic models for API contracts
- Add or update tests in `backend/tests/` for new behavior
- Keep business logic in services, not route handlers

### Frontend (TypeScript / React)

- Match existing component and hook patterns in `frontend/src/`
- Prefer functional components and explicit types
- Avoid large inline styles; use existing CSS modules / global styles
- Handle loading and error states for async operations

### General

- Do not commit secrets, `.env` files, or local database paths
- Minimize scope — fix one thing per PR when possible
- Update `README.md`, `CHANGELOG.md`, or `docs/` when behavior or setup changes

---

## Reporting Issues

### Bug reports

Include:

- DroidLens version
- OS and versions of Node.js / Python
- Android device or emulator details (if relevant)
- Steps to reproduce
- Expected vs. actual behavior
- Logs or screenshots

### Feature requests

Describe the problem you're solving, proposed behavior, and any alternatives considered.

---

## Admin & Licensing Development

For local development, the subscription system defaults to **disabled** — authenticated users receive premium access without payment. Enable it via **Admin → System Settings** to test trial, payment, and gating flows.

---

## Questions?

Reach out to [info.kiranc@gmail.com](mailto:info.kiranc@gmail.com) or open a Discussion/Issue on the repository.

Thank you for helping make DroidLens better for the automation community!
