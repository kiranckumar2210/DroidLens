"""Auth repository factory — SQLite when available, JSON file otherwise."""

from __future__ import annotations

import logging
from typing import Any, Optional

from inspectiq.auth.sqlite_compat import sqlite_available

logger = logging.getLogger(__name__)


def create_auth_repository(db_path: Optional[str] = None) -> Any:
    """Return SQLite or JSON-backed auth store depending on runtime capabilities."""
    if sqlite_available():
        from inspectiq.auth.sql_repository import SqlAuthRepository

        repo = SqlAuthRepository(db_path)
        logger.info("Auth store: SQLite at %s", repo.db_path)
        return repo

    from inspectiq.auth.json_repository import JsonAuthRepository

    repo = JsonAuthRepository(db_path)
    logger.warning(
        "Python _sqlite3 unavailable — using JSON auth store at %s. "
        "For SQLite: pip install pysqlite3-binary, or install python3-sqlite3 for your Python build.",
        repo.db_path,
    )
    return repo
