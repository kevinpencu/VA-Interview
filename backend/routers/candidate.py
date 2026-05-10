"""Candidate-side endpoints: /api/test/<token>/*"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response

from auth import verify_candidate_session
from config import load_settings
from models import StartRequest, StateResponse
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


def _resolve_state(candidate: dict | None, cookie: str | None) -> StateResponse:
    if candidate is None or candidate.get("link_used"):
        return StateResponse(state="invalid")
    if not candidate.get("started_at"):
        return StateResponse(state="needs_name")
    # Started — must have a matching cookie to proceed
    if cookie != candidate.get("session_id"):
        return StateResponse(state="session_in_use")
    # Detailed state (tutorial/quiz/step) computed in later tasks
    return StateResponse(state="needs_tutorial")


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
