"""Apply runtime patches before any SQLAlchemy/SQLite usage."""

from __future__ import annotations

from inspectiq.auth.sqlite_compat import ensure_sqlite3

ensure_sqlite3()
