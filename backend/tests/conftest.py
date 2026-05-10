"""Shared fixtures: mocked Supabase client + FastAPI TestClient."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Stub env vars so config.load_settings() works in tests."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("MANAGER_EMAIL", "manager@example.com")


def _patch_get_supabase_everywhere(monkeypatch, mock):
    """Patch the get_supabase name in supabase_client AND in every router
    module that imported it (since `from x import y` binds the name at
    import time and a setattr on `x` won't affect those bindings)."""
    import supabase_client
    if hasattr(supabase_client.get_supabase, "cache_clear"):
        supabase_client.get_supabase.cache_clear()
    monkeypatch.setattr(supabase_client, "get_supabase", lambda: mock)
    for mod_name, mod in list(sys.modules.items()):
        if mod_name.startswith("routers.") and getattr(mod, "get_supabase", None) is not None:
            monkeypatch.setattr(mod, "get_supabase", lambda: mock)


@pytest.fixture
def mock_supabase(monkeypatch):
    """Replace get_supabase() with a MagicMock everywhere it has been imported."""
    mock = MagicMock(name="supabase_client")
    _patch_get_supabase_everywhere(monkeypatch, mock)
    return mock


@pytest.fixture
def client(mock_supabase, monkeypatch) -> TestClient:
    from main import app
    # main.py may have transitively imported routers — re-run the consumer
    # patch now that any new router modules are in sys.modules.
    _patch_get_supabase_everywhere(monkeypatch, mock_supabase)
    return TestClient(app)
