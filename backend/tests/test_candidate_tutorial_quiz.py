"""Tests for /tutorial-acknowledged and /quiz."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock


CID = str(uuid.uuid4())


def _candidate(**overrides):
    base = {
        "id": CID,
        "invite_token": "tok-abc",
        "session_id": "sess-1",
        "started_at": "2026-05-10T00:00:00Z",
        "submitted_at": None,
        "link_used": False,
        "forced_justification_indexes": None,
    }
    base.update(overrides)
    return base


def _wire(mock, *, candidate, has_event=False, quiz_count=0, questions=None):
    """Wire up the most common chain calls used by these tests."""
    table = mock.table

    def _select_single(value):
        return MagicMock(execute=MagicMock(return_value=MagicMock(data=value)))

    def candidates_select(*_a, **_k):
        return MagicMock(eq=lambda *_a, **_k: MagicMock(single=lambda: _select_single(candidate)))

    def events_select(*_a, **_k):
        return MagicMock(eq=lambda *_a, **_k: MagicMock(eq=lambda *_a, **_k: MagicMock(
            limit=lambda *_a, **_k: MagicMock(execute=lambda: MagicMock(data=[1] if has_event else []))
        )))

    def quiz_answers_select(*_a, **_k):
        return MagicMock(eq=lambda *_a, **_k: MagicMock(execute=lambda: MagicMock(count=quiz_count)))

    def quiz_questions_select(*_a, **_k):
        return MagicMock(order=lambda *_a, **_k: MagicMock(execute=lambda: MagicMock(data=questions or [])))

    insert_chain = MagicMock(execute=MagicMock())
    update_chain = MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock())))
    # Shared mocks per-table so tests can inspect call args after the fact.
    candidates_table = MagicMock()
    candidates_table.select = MagicMock(side_effect=candidates_select)
    candidates_table.update = MagicMock(return_value=update_chain)
    events_table = MagicMock()
    events_table.select = MagicMock(side_effect=events_select)
    events_table.insert = MagicMock(return_value=insert_chain)
    quiz_answers_table = MagicMock()
    quiz_answers_table.select = MagicMock(side_effect=quiz_answers_select)
    quiz_answers_table.insert = MagicMock(return_value=insert_chain)
    quiz_questions_table = MagicMock()
    quiz_questions_table.select = MagicMock(side_effect=quiz_questions_select)

    def table_router(name):
        if name == "candidates":
            return candidates_table
        if name == "candidate_events":
            return events_table
        if name == "candidate_quiz_answers":
            return quiz_answers_table
        if name == "quiz_questions":
            return quiz_questions_table
        return MagicMock()

    table.side_effect = table_router
    # Expose the candidates-table mock so tests can assert against it.
    mock._candidates_table = candidates_table


def test_tutorial_ack_logs_event(client, mock_supabase):
    cand = _candidate()
    _wire(mock_supabase, candidate=cand, has_event=False, quiz_count=0)
    r = client.post(
        "/api/test/tok-abc/tutorial-acknowledged",
        cookies={"session_id": "sess-1"},
    )
    assert r.status_code == 200
    # Insert into candidate_events called
    mock_supabase.table.assert_any_call("candidate_events")


def test_quiz_pass_advances_state(client, mock_supabase):
    cand = _candidate()
    questions = [{"id": str(uuid.uuid4()), "correct_index": i % 4, "display_order": i} for i in range(5)]
    _wire(mock_supabase, candidate=cand, has_event=True, quiz_count=0, questions=questions)
    answers = [q["correct_index"] for q in questions]   # all correct
    r = client.post("/api/test/tok-abc/quiz",
                    json={"answers": answers},
                    cookies={"session_id": "sess-1"})
    assert r.status_code == 200
    assert r.json() == {"passed": True, "score": 5}


def test_quiz_fail_marks_link_used(client, mock_supabase):
    cand = _candidate()
    questions = [{"id": str(uuid.uuid4()), "correct_index": 0, "display_order": i} for i in range(5)]
    _wire(mock_supabase, candidate=cand, has_event=True, quiz_count=0, questions=questions)
    # 2/5 correct
    answers = [0, 0, 1, 1, 1]
    r = client.post("/api/test/tok-abc/quiz",
                    json={"answers": answers},
                    cookies={"session_id": "sess-1"})
    assert r.status_code == 200
    assert r.json() == {"passed": False, "score": 2}
    # update was called on candidates with link_used=True
    update_calls = mock_supabase._candidates_table.update.call_args_list
    assert any("link_used" in str(call) for call in update_calls)
