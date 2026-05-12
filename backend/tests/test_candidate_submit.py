"""Verify /submit calls compute_recommendation with correctly assembled stats."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch


def test_submit_writes_recommendation(client, mock_supabase):
    cid = str(uuid.uuid4())
    cand = {
        "id": cid,
        "invite_token": "tok",
        "session_id": "s",
        "link_used": False,
        "submitted_at": None,
        "started_at": "2026-05-10T00:00:00Z",
        "forced_justification_indexes": None,
    }

    # 90 decisions total, 30 per pool — enough to satisfy ITEMS_PER_STEP gating.
    decision_rows = [{"pool": p} for p in (
        ["tiktok"] * 30 + ["nano_banana"] * 30 + ["kling"] * 30
    )]

    candidates_table = MagicMock()
    # candidates.select(...).eq(...).single().execute()
    candidates_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=cand)
    # candidates.update(...).eq(...).execute()
    candidates_update_chain = MagicMock()
    candidates_table.update.return_value.eq.return_value.execute.return_value = candidates_update_chain

    decisions_table = MagicMock()
    # candidate_decisions.select("pool").eq("candidate_id", cid).execute() — used by _step_progress
    decisions_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=decision_rows)

    events_table = MagicMock()
    # _has_event chain: select("id").eq().eq().limit(1).execute()
    events_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[1])

    quiz_answers_table = MagicMock()
    # _quiz_answered: select("id", count="exact").eq(...).execute() — needs .count attribute
    quiz_answers_table.select.return_value.eq.return_value.execute.return_value = MagicMock(count=5)

    def _table(name):
        if name == "candidates":
            return candidates_table
        if name == "candidate_decisions":
            return decisions_table
        if name == "candidate_events":
            return events_table
        if name == "candidate_quiz_answers":
            return quiz_answers_table
        return MagicMock()

    mock_supabase.table.side_effect = _table

    # Patch _build_scoring_input to skip heavy assembly. Pass perfect stats so
    # compute_recommendation returns "pass" with no fail reasons.
    from scoring import ScoringInput, StepStats
    perfect = StepStats(accuracy=1.0, duplicate_consistency=0, expected_duplicates=0)
    perfect_input = ScoringInput(
        quiz_score=5, tab_switches=0,
        tiktok=perfect, nano_banana=perfect, kling=perfect,
    )
    with patch("routers.candidate._build_scoring_input", return_value=perfect_input):
        r = client.post("/api/test/tok/submit", cookies={"session_id": "s"})

    assert r.status_code == 200, r.text
    # Verify the candidates row was updated with a recommendation.
    update_calls = candidates_table.update.call_args_list
    assert update_calls, "expected candidates.update() to be called"
    payload = update_calls[0].args[0]
    assert payload["recommendation"] == "pass"
    assert payload["auto_fail_reasons"] == []
    assert payload["link_used"] is True
    assert "submitted_at" in payload


def test_submit_rejects_incomplete_test(client, mock_supabase):
    cid = str(uuid.uuid4())
    cand = {
        "id": cid,
        "invite_token": "tok",
        "session_id": "s",
        "link_used": False,
        "submitted_at": None,
        "started_at": "2026-05-10T00:00:00Z",
        "forced_justification_indexes": None,
    }
    # Only 10 decisions across all pools — not complete.
    decision_rows = [{"pool": "tiktok"} for _ in range(10)]

    candidates_table = MagicMock()
    candidates_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=cand)

    decisions_table = MagicMock()
    decisions_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=decision_rows)

    def _table(name):
        if name == "candidates":
            return candidates_table
        if name == "candidate_decisions":
            return decisions_table
        return MagicMock()

    mock_supabase.table.side_effect = _table

    r = client.post("/api/test/tok/submit", cookies={"session_id": "s"})
    assert r.status_code == 409
