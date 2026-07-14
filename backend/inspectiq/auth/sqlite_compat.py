"""Ensure sqlite3 is available before SQLAlchemy opens a SQLite database."""

from __future__ import annotations

import sys

_SQLITE_OK = False


def ensure_sqlite3() -> bool:
    global _SQLITE_OK
    if _SQLITE_OK:
        return True
    if 'sqlite3' in sys.modules:
        mod = sys.modules['sqlite3']
        if hasattr(mod, 'connect'):
            _SQLITE_OK = True
            return True

    try:
        import sqlite3  # noqa: F401
        if hasattr(sqlite3, 'connect'):
            _SQLITE_OK = True
            return True
    except (ModuleNotFoundError, ImportError):
        pass

    try:
        import pysqlite3
        sys.modules['sqlite3'] = pysqlite3
        _SQLITE_OK = True
        return True
    except (ModuleNotFoundError, ImportError):
        return False


def sqlite_available() -> bool:
    return ensure_sqlite3()
