# DroidLens — Database Schema

SQLite database stored at `~/.droidlens/droidlens.db` (legacy: `~/.inspectiq/inspectiq.db`).

## Tables

- **projects** — Top-level automation projects
- **features** — Feature areas within a project
- **screens** — Screen/page definitions per platform
- **saved_elements** — Captured UI elements with properties JSON
- **locator_records** — Generated locators with scores
- **artifacts** — Screenshot and XML paths per saved element

See `backend/inspectiq/storage/database.py` for ORM definitions.
