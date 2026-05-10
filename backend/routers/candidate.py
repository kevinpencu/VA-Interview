"""Candidate-side endpoints: /api/test/<token>/*"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response

from auth import verify_candidate_session
from config import QUIZ_PASS_THRESHOLD, load_settings
from models import EventRequest, QuizRequest, QuizResponse, StartRequest, StateResponse
from supabase_client import get_supabase

router = APIRouter(prefix="/api/test/{token}", tags=["candidate"])

SESSION_COOKIE = "session_id"


def _get_candidate(token: str) -> dict | None:
    res = (
        get_supabase()
        .table("candidates")
        .select("*")
        .eq("invite_token", token)
        .single()
        .execute()
    )
    return res.data


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_event(candidate_id: str, kind: str) -> bool:
    res = (
        get_supabase()
        .table("candidate_events")
        .select("id")
        .eq("candidate_id", candidate_id)
        .eq("kind", kind)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def _quiz_answered(candidate_id: str) -> bool:
    res = (
        get_supabase()
        .table("candidate_quiz_answers")
        .select("id", count="exact")
        .eq("candidate_id", candidate_id)
        .execute()
    )
    return (res.count or 0) >= 5


def _resolve_state(candidate: dict | None, cookie: str | None) -> StateResponse:
    if candidate is None or candidate.get("link_used"):
        return StateResponse(state="invalid")
    if not candidate.get("started_at"):
        return StateResponse(state="needs_name")
    if cookie != candidate.get("session_id"):
        return StateResponse(state="session_in_use")
    if candidate.get("submitted_at"):
        return StateResponse(state="submitted")
    cid = candidate["id"]
    if not _has_event(cid, "tutorial_view"):
        return StateResponse(state="needs_tutorial")
    if not _quiz_answered(cid):
        return StateResponse(state="needs_quiz")
    # Step routing computed in Task 11. Until then default to first step intro.
    return StateResponse(state="step_tiktok_intro")


@router.get("/state", response_model=StateResponse)
def state(token: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    return _resolve_state(candidate, session_id)


@router.post("/start", response_model=StateResponse)
def start(token: str, body: StartRequest, response: Response) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    if candidate.get("link_used"):
        raise HTTPException(410, "Link already used")
    if candidate.get("started_at") or candidate.get("session_id"):
        raise HTTPException(409, "Test already in progress")

    new_session = secrets.token_urlsafe(32)
    now = _now_iso()
    update = {
        "candidate_name": body.name,
        "candidate_email": body.email,
        "session_id": new_session,
        "started_at": now,
    }
    get_supabase().table("candidates").update(update).eq("invite_token", token).execute()

    settings = load_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=new_session,
        max_age=settings.session_cookie_max_age_seconds,
        httponly=True,
        samesite="lax",
        path=f"/api/test/{token}",
    )
    return StateResponse(state="needs_tutorial")


@router.post("/tutorial-acknowledged", response_model=StateResponse)
def tutorial_ack(token: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]
    if not _has_event(cid, "tutorial_view"):
        get_supabase().table("candidate_events").insert({
            "candidate_id": cid,
            "kind": "tutorial_view",
        }).execute()
    return _resolve_state(_get_candidate(token), session_id)


@router.post("/quiz", response_model=QuizResponse)
def submit_quiz(token: str, body: QuizRequest, session_id: str | None = Cookie(default=None)) -> QuizResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]
    if _quiz_answered(cid):
        raise HTTPException(409, "Quiz already submitted")

    # Fetch the 5 questions in display_order
    qres = (
        get_supabase()
        .table("quiz_questions")
        .select("id,correct_index,display_order")
        .order("display_order")
        .execute()
    )
    questions = qres.data or []
    if len(questions) != 5:
        raise HTTPException(500, f"Expected 5 quiz questions, got {len(questions)}")

    score = 0
    rows_to_insert = []
    for idx, q in enumerate(questions):
        answered = body.answers[idx]
        is_correct = answered == q["correct_index"]
        if is_correct:
            score += 1
        rows_to_insert.append({
            "candidate_id": cid,
            "question_id": q["id"],
            "answered_index": answered,
            "is_correct": is_correct,
        })
    get_supabase().table("candidate_quiz_answers").insert(rows_to_insert).execute()

    passed = score >= QUIZ_PASS_THRESHOLD
    if not passed:
        # Auto-fail immediately. Mark link used, set recommendation.
        get_supabase().table("candidates").update({
            "link_used": True,
            "submitted_at": _now_iso(),
            "recommendation": "fail",
            "auto_fail_reasons": ["failed_quiz"],
        }).eq("id", cid).execute()
    return QuizResponse(passed=passed, score=score)
