import os

import pytest

import inspectiq.bootstrap  # noqa: F401 — patch sqlite3 before app import

os.environ.setdefault("DROIDLENS_MOCK", "true")
os.environ.setdefault("INSPECTIQ_MOCK", "true")


@pytest.fixture
def paid_licensing_mode(monkeypatch):
    """Enable subscription/billing paths — default app mode is free service."""
    monkeypatch.setenv("DROIDLENS_FREE_MODE", "false")
    monkeypatch.setenv("DROIDLENS_SUBSCRIPTION_ENABLED", "true")
    from inspectiq.auth.system_settings_service import get_system_settings_service

    get_system_settings_service().invalidate_cache()
    yield
    get_system_settings_service().invalidate_cache()
