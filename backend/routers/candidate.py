"""Candidate-side endpoints: /api/test/<token>/*"""
from __future__ import annotations

import functools
import random as _random
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Response

from auth import verify_candidate_session
from config import (
    FORCED_JUSTIFICATIONS_PER_STEP,
    ITEMS_PER_STEP,
    POOLS,
    QUIZ_PASS_THRESHOLD,
    QUIZ_QUESTION_COUNT,
    load_settings,
)
from models import (
    DecisionRequest,
    DecisionResponse,
    DecisionResponseNext,
    EventRequest,
    JustificationRequest,
    QuizRequest,
    QuizResponse,
    StartRequest,
    StateResponse,
    StateResponseItem,
)
from scoring import ScoringInput, StepStats, compute_recommendation
from storage import signed_url_for_item
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
    return (res.count or 0) >= QUIZ_QUESTION_COUNT


def _candidate_decisions_for_step(candidate_id: str, pool: str) -> list[dict]:
    res = (
        get_supabase()
        .table("candidate_decisions")
        .select("*")
        .eq("candidate_id", candidate_id)
        .eq("pool", pool)
        .order("display_index")
        .execute()
    )
    return res.data or []


@functools.lru_cache(maxsize=8)
def _cached_items_for_pool(pool: str) -> tuple[dict, ...]:
    """Test_items for a pool, cached process-locally. Restart server after re-seeding."""
    res = get_supabase().table("test_items").select("*").eq("pool", pool).execute()
    return tuple(res.data or [])


def _items_for_pool(pool: str) -> list[dict]:
    return list(_cached_items_for_pool(pool))


@functools.lru_cache(maxsize=2048)
def _cached_sequence_for_session(session_id: str, pool: str) -> tuple[dict, ...]:
    """Deterministic per-candidate item sequence. Cached so /decision doesn't
    rebuild + re-query test_items on every click. Each session_id is unique
    per candidate session so the cache never replays stale data."""
    rng = _random.Random(f"{session_id}:{pool}")
    return tuple(_build_step_sequence(pool, rng))


def _build_step_sequence(pool: str, rng: _random.Random) -> list[dict]:
    """Return a list of item dicts in the order to be shown.

    Originals (rows where duplicate_of_item IS NULL) are shuffled. Then any
    rows where duplicate_of_item references an original in this pool are
    inserted at a later random position.

    Returns dicts with keys: item_id, is_duplicate, original_index (or None).
    """
    items = _items_for_pool(pool)
    originals = [i for i in items if i.get("duplicate_of_item") is None]
    dupes = [i for i in items if i.get("duplicate_of_item") is not None]

    if not originals:
        raise HTTPException(500, f"Insufficient items in pool {pool}")

    shuffled = list(originals)
    rng.shuffle(shuffled)
    sequence = [
        {"item_id": i["id"], "is_duplicate": False, "original_index": None}
        for i in shuffled
    ]

    def _pos_of(item_id: str) -> int | None:
        for idx, entry in enumerate(sequence):
            if entry["item_id"] == item_id and not entry["is_duplicate"]:
                return idx
        return None

    for dupe in dupes:
        original_item_id = dupe["duplicate_of_item"]
        original_pos = _pos_of(original_item_id)
        if original_pos is None:
            # Dupe references an item not present in this pool's originals — skip defensively.
            continue
        insert_at = rng.randint(original_pos + 1, len(sequence))
        new_entry = {
            "item_id": dupe["id"],
            "is_duplicate": True,
            "original_index": original_pos,
        }
        # Bump previously stored original_index for any earlier-inserted dupe
        # whose original now shifts right by 1 due to this insertion.
        for entry in sequence:
            if entry["is_duplicate"] and entry["original_index"] is not None \
                    and entry["original_index"] >= insert_at:
                entry["original_index"] += 1
        sequence.insert(insert_at, new_entry)

    return sequence


def _ensure_step_started(candidate: dict, pool: str) -> tuple[list[dict], list[int]]:
    """If the candidate has not started this step, build & return the sequence and forced-justification indexes.

    Sequence is materialized lazily as the candidate answers (we don't pre-insert decision rows).
    Forced-justification indexes are persisted on candidates.forced_justification_indexes the first time the step starts.
    Returns (full_sequence, forced_indexes).
    """
    cid = candidate["id"]
    forced = (candidate.get("forced_justification_indexes") or {}).get(pool)

    # Deterministic per (session_id, pool) — cached process-locally so /decision
    # doesn't re-shuffle and re-query test_items on every click.
    sequence = list(_cached_sequence_for_session(candidate["session_id"], pool))

    if forced is None:
        forced = sorted(rng.sample(range(len(sequence)), FORCED_JUSTIFICATIONS_PER_STEP))
        all_forced = candidate.get("forced_justification_indexes") or {}
        all_forced[pool] = forced
        get_supabase().table("candidates").update({
            "forced_justification_indexes": all_forced,
        }).eq("id", cid).execute()
        # also log step_start
        get_supabase().table("candidate_events").insert({
            "candidate_id": cid, "kind": "step_start", "meta": {"pool": pool},
        }).execute()

    return sequence, forced


def _next_item_for_step(candidate: dict, pool: str) -> StateResponseItem | None:
    cid = candidate["id"]
    sequence, _forced = _ensure_step_started(candidate, pool)
    decisions = _candidate_decisions_for_step(cid, pool)
    next_idx = len(decisions)
    if next_idx >= ITEMS_PER_STEP:
        return None
    item_id = sequence[next_idx]["item_id"]
    item = get_supabase().table("test_items").select("*").eq("id", item_id).single().execute().data
    ref_path = item.get("reference_path")
    reference_url = signed_url_for_item(pool, ref_path) if ref_path else None
    return StateResponseItem(
        id=item_id,
        storage_url=signed_url_for_item(pool, item["storage_path"]),
        pool=pool,
        display_index=next_idx,
        reference_url=reference_url,
    )


def _step_progress(candidate_id: str) -> dict[str, int]:
    out = {p: 0 for p in POOLS}
    rows = (
        get_supabase()
        .table("candidate_decisions")
        .select("pool")
        .eq("candidate_id", candidate_id)
        .execute()
    ).data or []
    for r in rows:
        out[r["pool"]] = out.get(r["pool"], 0) + 1
    return out


def _has_intro_acked(candidate_id: str, pool: str) -> bool:
    res = (
        get_supabase()
        .table("candidate_events")
        .select("id,meta")
        .eq("candidate_id", candidate_id)
        .eq("kind", "step_start")
        .execute()
    )
    rows = res.data or []
    return any((r.get("meta") or {}).get("intro_acked") and (r.get("meta") or {}).get("pool") == pool for r in rows)


def _next_pool(pool: str) -> str | None:
    idx = POOLS.index(pool)
    return POOLS[idx + 1] if idx + 1 < len(POOLS) else None


def _resolve_state(candidate: dict | None, cookie: str | None) -> StateResponse:
    if candidate is None:
        return StateResponse(state="invalid")
    # Submitted (or quiz-failed-and-finalized) candidates see the thank-you page
    # regardless of cookie, even from a new tab.
    if candidate.get("submitted_at"):
        return StateResponse(state="submitted")
    if candidate.get("link_used"):
        return StateResponse(state="invalid")
    if not candidate.get("started_at"):
        return StateResponse(state="needs_name")
    if cookie != candidate.get("session_id"):
        return StateResponse(state="session_in_use")
    cid = candidate["id"]
    if not _has_event(cid, "tutorial_view"):
        return StateResponse(state="needs_tutorial")
    if not _quiz_answered(cid):
        return StateResponse(state="needs_quiz")
    progress = _step_progress(cid)
    for pool in POOLS:
        if progress[pool] == 0 and not _has_intro_acked(cid, pool):
            return StateResponse(state=f"step_{pool}_intro")
        if progress[pool] < ITEMS_PER_STEP:
            next_item = _next_item_for_step(candidate, pool)
            return StateResponse(
                state=f"step_{pool}_in_progress",
                progress_in_step=progress[pool],
                next_item=next_item,
            )
    # All steps complete but not submitted yet
    return StateResponse(state="step_kling_in_progress")  # caller should call /submit


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
        secure=settings.cookie_secure,
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
    if len(questions) != QUIZ_QUESTION_COUNT:
        raise HTTPException(500, f"Expected {QUIZ_QUESTION_COUNT} quiz questions, got {len(questions)}")

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


@router.post("/step/{pool}/intro-acknowledged", response_model=StateResponse)
def step_intro_ack(token: str, pool: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    if pool not in POOLS:
        raise HTTPException(404, "Unknown pool")
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    if not _has_intro_acked(candidate["id"], pool):
        get_supabase().table("candidate_events").insert({
            "candidate_id": candidate["id"],
            "kind": "step_start",
            "meta": {"pool": pool, "intro_acked": True},
        }).execute()
    return _resolve_state(_get_candidate(token), session_id)


@router.post("/decision", response_model=DecisionResponse)
def decision(token: str, body: DecisionRequest, session_id: str | None = Cookie(default=None)) -> DecisionResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]

    item = get_supabase().table("test_items").select("*").eq("id", body.item_id).single().execute().data
    if item is None:
        raise HTTPException(404, "Unknown item")
    pool = item["pool"]
    sequence, forced = _ensure_step_started(candidate, pool)
    progress = _step_progress(cid)
    expected_idx = progress[pool]
    if expected_idx >= ITEMS_PER_STEP:
        raise HTTPException(409, f"Step {pool} already complete")
    expected_id = sequence[expected_idx]["item_id"]
    if expected_id != body.item_id:
        raise HTTPException(409, f"Out of order item; expected {expected_id}")

    is_correct = body.answer == item["correct_answer"]
    forced_now = expected_idx in forced
    duplicate_of = None
    if sequence[expected_idx]["is_duplicate"]:
        original_idx = sequence[expected_idx]["original_index"]
        prior = (
            get_supabase().table("candidate_decisions")
            .select("id").eq("candidate_id", cid).eq("pool", pool).eq("display_index", original_idx)
            .single().execute().data
        )
        duplicate_of = (prior or {}).get("id")

    try:
        inserted = (
            get_supabase().table("candidate_decisions").insert({
                "candidate_id": cid,
                "item_id": body.item_id,
                "pool": pool,
                "display_index": expected_idx,
                "answer": body.answer,
                "is_correct": is_correct,
                "dwell_ms": body.dwell_ms,
                "shown_at": body.shown_at.isoformat(),
                "forced_justification": forced_now,
                "duplicate_of": duplicate_of,
            }).execute()
        )
    except Exception as e:
        # The unique constraint on (candidate_id, pool, display_index) catches
        # double-submit races (e.g., a frontend double-click that slipped past
        # the disabled-button guard). Return 409 cleanly instead of a 500.
        msg = str(e).lower()
        if "23505" in msg or "duplicate key" in msg or "unique" in msg:
            raise HTTPException(409, "Decision already recorded — refresh to continue")
        raise
    decision_id = inserted.data[0]["id"]

    # Build next response
    next_progress = expected_idx + 1
    if next_progress >= ITEMS_PER_STEP:
        # log step_end
        get_supabase().table("candidate_events").insert({
            "candidate_id": cid, "kind": "step_end", "meta": {"pool": pool},
        }).execute()
        next_pool = _next_pool(pool)
        if next_pool is None:
            return DecisionResponse(
                decision_id=decision_id,
                needs_justification=forced_now,
                next=DecisionResponseNext(test_complete=True),
            )
        return DecisionResponse(
            decision_id=decision_id,
            needs_justification=forced_now,
            next=DecisionResponseNext(step_complete=True),
        )

    next_item_id = sequence[next_progress]["item_id"]
    next_item_row = get_supabase().table("test_items").select("*").eq("id", next_item_id).single().execute().data
    next_ref_path = next_item_row.get("reference_path")
    next_reference_url = signed_url_for_item(pool, next_ref_path) if next_ref_path else None
    next_item_payload = StateResponseItem(
        id=next_item_id,
        storage_url=signed_url_for_item(pool, next_item_row["storage_path"]),
        pool=pool,
        display_index=next_progress,
        reference_url=next_reference_url,
    )
    return DecisionResponse(
        decision_id=decision_id,
        needs_justification=forced_now,
        next=DecisionResponseNext(item=next_item_payload),
    )


@router.post("/justification", response_model=StateResponse)
def justification(token: str, body: JustificationRequest, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    # Confirm the decision belongs to this candidate
    dec = (
        get_supabase().table("candidate_decisions")
        .select("id,candidate_id,forced_justification")
        .eq("id", body.decision_id).single().execute().data
    )
    if dec is None or dec["candidate_id"] != candidate["id"]:
        raise HTTPException(404, "Unknown decision")
    if not dec["forced_justification"]:
        raise HTTPException(409, "Decision did not require justification")
    get_supabase().table("candidate_decisions").update({
        "justification": body.justification,
    }).eq("id", body.decision_id).execute()
    return _resolve_state(_get_candidate(token), session_id)


@router.post("/event", response_model=StateResponse)
def event(token: str, body: EventRequest, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    get_supabase().table("candidate_events").insert({
        "candidate_id": candidate["id"],
        "kind": body.kind,
        "meta": body.meta,
    }).execute()
    return _resolve_state(_get_candidate(token), session_id)


def _build_scoring_input(cid: str) -> ScoringInput:
    decisions = (
        get_supabase().table("candidate_decisions")
        .select("*").eq("candidate_id", cid).execute()
    ).data or []
    items_by_id = {
        i["id"]: i for i in (
            get_supabase().table("test_items").select("*").execute()
        ).data or []
    }
    quiz = (
        get_supabase().table("candidate_quiz_answers")
        .select("is_correct").eq("candidate_id", cid).execute()
    ).data or []
    events = (
        get_supabase().table("candidate_events")
        .select("kind").eq("candidate_id", cid).eq("kind", "tab_blur").execute()
    ).data or []

    def _expected_duplicates(pool: str) -> int:
        return sum(
            1 for i in items_by_id.values()
            if i["pool"] == pool and i.get("duplicate_of_item") is not None
        )

    def _step_stats(pool: str) -> StepStats:
        step_decisions = [d for d in decisions if d["pool"] == pool]
        expected_dupes = _expected_duplicates(pool)
        if not step_decisions:
            return StepStats(0.0, 0, expected_dupes)
        correct = sum(1 for d in step_decisions if d["is_correct"])
        accuracy = correct / len(step_decisions)
        # Duplicate consistency: same answer on dupe pair
        dupes = [d for d in step_decisions if d["duplicate_of"] is not None]
        dupe_consistency = 0
        for d in dupes:
            original = next((x for x in step_decisions if x["id"] == d["duplicate_of"]), None)
            if original is not None and original["answer"] == d["answer"]:
                dupe_consistency += 1
        return StepStats(
            accuracy=accuracy,
            duplicate_consistency=dupe_consistency,
            expected_duplicates=expected_dupes,
        )

    return ScoringInput(
        quiz_score=sum(1 for q in quiz if q["is_correct"]),
        tab_switches=len(events),
        tiktok=_step_stats("tiktok"),
        nano_banana=_step_stats("nano_banana"),
        kling=_step_stats("kling"),
    )


@router.post("/submit", response_model=StateResponse)
def submit(token: str, session_id: str | None = Cookie(default=None)) -> StateResponse:
    candidate = _get_candidate(token)
    if candidate is None:
        raise HTTPException(404, "Invalid invite link")
    verify_candidate_session(candidate, session_id)
    cid = candidate["id"]
    progress = _step_progress(cid)
    if any(progress[p] < ITEMS_PER_STEP for p in POOLS):
        raise HTTPException(409, "Test not complete")
    inp = _build_scoring_input(cid)
    rec, reasons = compute_recommendation(inp)
    get_supabase().table("candidates").update({
        "submitted_at": _now_iso(),
        "link_used": True,
        "recommendation": rec,
        "auto_fail_reasons": reasons,
    }).eq("id", cid).execute()
    return _resolve_state(_get_candidate(token), session_id)
