"""Shared fixtures: mocked Supabase client + FastAPI TestClient."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure backend/ is FIRST on sys.path so `import main` finds backend/main.py,
# not any stray main.py in the parent project root (e.g. PyCharm boilerplate).
_BACKEND = str(Path(__file__).resolve().parent.parent)
if _BACKEND in sys.path:
    sys.path.remove(_BACKEND)
sys.path.insert(0, _BACKEND)
# If pytest's rootdir-based path resolution already imported the wrong `main`,
# evict it so the next import resolves against backend/main.py.
_existing_main = sys.modules.get("main")
if _existing_main is not None and getattr(_existing_main, "__file__", "") and \
        not _existing_main.__file__.startswith(_BACKEND):
    del sys.modules["main"]

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
    # Re-assert backend/ at the front of sys.path right before importing main,
    # in case pytest's later path tweaks pushed the project root ahead of us.
    if sys.path[0] != _BACKEND:
        if _BACKEND in sys.path:
            sys.path.remove(_BACKEND)
        sys.path.insert(0, _BACKEND)
    _stale = sys.modules.get("main")
    if _stale is not None and getattr(_stale, "__file__", "") and \
            not _stale.__file__.startswith(_BACKEND):
        del sys.modules["main"]
    from main import app
    # main.py may have transitively imported routers — re-run the consumer
    # patch now that any new router modules are in sys.modules.
    _patch_get_supabase_everywhere(monkeypatch, mock_supabase)
    return TestClient(app)
