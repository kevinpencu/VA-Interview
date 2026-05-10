"""Tests for /api/test/<token>/state and /start."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock


def _candidate_row(**overrides):
    base = {
        "id": str(uuid.uuid4()),
        "invite_token": "tok-abc",
        "session_id": None,
        "started_at": None,
        "submitted_at": None,
        "link_used": False,
        "candidate_name": None,
        "candidate_email": None,
        "forced_justification_indexes": None,
    }
    base.update(overrides)
    return base


def _setup_select_single(mock_supabase, table: str, value):
    """Configure mock_supabase.table(<table>).select(...).eq(...).single().execute() = value."""
    table_chain = mock_supabase.table.return_value
    select_chain = table_chain.select.return_value
    eq_chain = select_chain.eq.return_value
    single_chain = eq_chain.single.return_value
    single_chain.execute.return_value = MagicMock(data=value)


def test_state_unknown_token_is_invalid(client, mock_supabase):
    _setup_select_single(mock_supabase, "candidates", None)
    r = client.get("/api/test/nope/state")
    assert r.status_code == 200
    assert r.json()["state"] == "invalid"


def test_state_unstarted_candidate_returns_needs_name(client, mock_supabase):
    _setup_select_single(mock_supabase, "candidates", _candidate_row())
    r = client.get("/api/test/tok-abc/state")
    assert r.status_code == 200
    assert r.json()["state"] == "needs_name"


def test_state_used_link_returns_invalid(client, mock_supabase):
    _setup_select_single(mock_supabase, "candidates", _candidate_row(link_used=True))
    r = client.get("/api/test/tok-abc/state")
    assert r.json()["state"] == "invalid"


def test_state_started_session_without_cookie_returns_session_in_use(client, mock_supabase):
    row = _candidate_row(started_at="2026-05-10T00:00:00Z", session_id="sess-123")
    _setup_select_single(mock_supabase, "candidates", row)
    r = client.get("/api/test/tok-abc/state")
    assert r.json()["state"] == "session_in_use"


def test_start_creates_session_and_sets_cookie(client, mock_supabase):
    row = _candidate_row()
    _setup_select_single(mock_supabase, "candidates", row)
    update_chain = mock_supabase.table.return_value.update.return_value
    update_chain.eq.return_value.execute.return_value = MagicMock(data=[row])

    r = client.post("/api/test/tok-abc/start", json={"name": "Jane Doe", "email": "j@d.com"})
    assert r.status_code == 200
    assert "session_id" in r.cookies


def test_start_rejects_already_started(client, mock_supabase):
    row = _candidate_row(started_at="2026-05-10T00:00:00Z", session_id="sess-existing")
    _setup_select_single(mock_supabase, "candidates", row)
    r = client.post("/api/test/tok-abc/start", json={"name": "X", "email": "y@z.com"})
    assert r.status_code == 409


def test_start_rejects_used_link(client, mock_supabase):
    row = _candidate_row(link_used=True)
    _setup_select_single(mock_supabase, "candidates", row)
    r = client.post("/api/test/tok-abc/start", json={"name": "X", "email": "y@z.com"})
    assert r.status_code == 410
