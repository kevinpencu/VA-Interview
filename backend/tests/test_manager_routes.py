"""Manager route auth + happy paths (mocked Supabase)."""
from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock

import jwt


JWT_SECRET = "test-jwt-secret"


def _manager_jwt(email: str = "manager@example.com") -> str:
    payload = {
        "sub": str(uuid.uuid4()),
        "email": email,
        "exp": int(time.time()) + 3600,
        "aud": "authenticated",
        "role": "authenticated",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def test_invites_requires_auth(client):
    r = client.post("/api/manager/invites", json={"name": "x", "email": "x@y.com"})
    assert r.status_code == 401


def test_invites_rejects_wrong_email(client):
    tok = _manager_jwt("intruder@example.com")
    r = client.post(
        "/api/manager/invites",
        json={"name": "x", "email": "x@y.com"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 403


def test_invites_creates_row(client, mock_supabase):
    new_id = str(uuid.uuid4())
    insert_chain = mock_supabase.table.return_value.insert.return_value
    insert_chain.execute.return_value = MagicMock(data=[{"id": new_id}])

    tok = _manager_jwt()
    r = client.post(
        "/api/manager/invites",
        json={"name": "Jane Doe", "email": "j@d.com"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["candidate_id"] == new_id
    assert body["url"].endswith("/test/" + body["token"])


def test_list_candidates_returns_rows(client, mock_supabase):
    rows = [{
        "id": str(uuid.uuid4()),
        "invited_label": "Jane",
        "invited_label_email": "j@d.com",
        "candidate_name": None, "candidate_email": None,
        "created_at": "2026-05-10T00:00:00Z",
        "started_at": None, "submitted_at": None,
        "link_used": False, "recommendation": None, "manager_decision": None,
    }]
    chain = mock_supabase.table.return_value.select.return_value.order.return_value
    chain.execute.return_value = MagicMock(data=rows)

    tok = _manager_jwt()
    r = client.get("/api/manager/candidates", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert len(r.json()) == 1
