"""Shared fixtures: mocked Supabase client + FastAPI TestClient."""
from __future__ import annotations

import os
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


@pytest.fixture
def mock_supabase(monkeypatch):
    """Replace get_supabase() with a MagicMock. Tests configure return values per call."""
    mock = MagicMock(name="supabase_client")
    import supabase_client
    monkeypatch.setattr(supabase_client, "get_supabase", lambda: mock)
    # Also patch in the module that imports it
    return mock


@pytest.fixture
def client(mock_supabase) -> TestClient:
    from main import app
    return TestClient(app)
