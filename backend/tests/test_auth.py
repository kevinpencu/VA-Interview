"""Tests for auth.verify_manager_jwt and verify_candidate_session."""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi import HTTPException

from auth import verify_candidate_session, verify_manager_jwt


JWT_SECRET = "test-jwt-secret"


def _manager_token(email: str = "manager@example.com", exp_offset: int = 3600) -> str:
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": email,
        "exp": int(time.time()) + exp_offset,
        "aud": "authenticated",
        "role": "authenticated",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def test_verify_manager_jwt_accepts_correct_email():
    token = _manager_token()
    claims = verify_manager_jwt(f"Bearer {token}")
    assert claims["email"] == "manager@example.com"


def test_verify_manager_jwt_rejects_wrong_email():
    token = _manager_token(email="someone-else@example.com")
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt(f"Bearer {token}")
    assert exc.value.status_code == 403


def test_verify_manager_jwt_rejects_expired():
    token = _manager_token(exp_offset=-10)
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_verify_manager_jwt_rejects_missing_header():
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt(None)
    assert exc.value.status_code == 401


def test_verify_manager_jwt_rejects_malformed_header():
    with pytest.raises(HTTPException) as exc:
        verify_manager_jwt("Token abc")
    assert exc.value.status_code == 401


def test_verify_candidate_session_matches():
    # Candidate row has session_id 'sess-123' and link_used=False
    candidate = {"session_id": "sess-123", "link_used": False}
    # cookie value matches
    verify_candidate_session(candidate, cookie_value="sess-123")
    # no exception → success


def test_verify_candidate_session_rejects_mismatch():
    candidate = {"session_id": "sess-123", "link_used": False}
    with pytest.raises(HTTPException) as exc:
        verify_candidate_session(candidate, cookie_value="sess-other")
    assert exc.value.status_code == 409


def test_verify_candidate_session_rejects_missing_cookie():
    candidate = {"session_id": "sess-123", "link_used": False}
    with pytest.raises(HTTPException) as exc:
        verify_candidate_session(candidate, cookie_value=None)
    assert exc.value.status_code == 409


def test_verify_candidate_session_rejects_used_link():
    candidate = {"session_id": "sess-123", "link_used": True}
    with pytest.raises(HTTPException) as exc:
        verify_candidate_session(candidate, cookie_value="sess-123")
    assert exc.value.status_code == 410   # Gone
