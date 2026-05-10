"""Lighter integration tests for /decision — invariants only."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock


def test_decision_rejects_unknown_item(client, mock_supabase):
    """If item_id doesn't exist, 404."""
    cand = {
        "id": str(uuid.uuid4()), "session_id": "sess-1",
        "started_at": "2026-05-10T00:00:00Z", "link_used": False,
        "submitted_at": None, "forced_justification_indexes": None,
    }

    def _table(name):
        m = MagicMock()
        if name == "candidates":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=cand)
        elif name == "test_items":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        return m
    mock_supabase.table.side_effect = _table

    r = client.post(
        "/api/test/tok/decision",
        json={"item_id": str(uuid.uuid4()), "answer": True, "dwell_ms": 1000,
              "shown_at": "2026-05-10T00:01:00Z"},
        cookies={"session_id": "sess-1"},
    )
    assert r.status_code == 404
