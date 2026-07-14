"""Structured logging for live inspection diagnostics."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level=None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
