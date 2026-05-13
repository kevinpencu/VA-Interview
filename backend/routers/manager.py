"""Manager-side endpoints: /api/manager/*"""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from auth import verify_manager_jwt
from config import POOLS, ITEMS_PER_STEP
from models import (
    CandidateRow, CandidateDetail, CreateInviteRequest, CreateInviteResponse,
    PatchCandidateRequest, StepBreakdown,
)
from storage import signed_url_for_item
from supabase_client import get_supabase

router = APIRouter(prefix="/api/manager", tags=["manager"])


def _require_manager(authorization: str | None = Header(default=None)) -> dict:
    return verify_manager_jwt(authorization)


@router.post("/invites", response_model=CreateInviteResponse)
def create_invite(
    body: CreateInviteRequest,
    request: Request,
    claims: dict = Depends(_require_manager),
) -> CreateInviteResponse:
    token = secrets.token_urlsafe(24)
    res = (
        get_supabase().table("candidates").insert({
            "invite_token": token,
            "invited_by": claims.get("sub"),
            "invited_label": body.name,
            "invited_label_email": body.email,
        }).execute()
    )
    candidate_id = res.data[0]["id"]
    base = str(request.base_url).rstrip("/")
    return CreateInviteResponse(
        candidate_id=candidate_id,
        token=token,
        url=f"{base}/test/{token}",
    )


PREVIEW_LABEL = "__PREVIEW__"


@router.post("/preview-invite")
def create_preview_invite(_: dict = Depends(_require_manager)) -> dict:
    """Create a fresh, single-shot preview invite.

    Wipes all prior __PREVIEW__-labeled candidates (cascading their decisions,
    events, and quiz answers) then inserts a single new row. Frontend builds
    the candidate URL from its own window.location.origin so this works
    regardless of dev/prod deployment.
    """
    sb = get_supabase()
    sb.table("candidates").delete().eq("invited_label", PREVIEW_LABEL).execute()
    token = secrets.token_urlsafe(24)
    sb.table("candidates").insert({
        "invite_token": token,
        "invited_label": PREVIEW_LABEL,
        "invited_label_email": "preview@local.test",
    }).execute()
    return {"token": token}


def _row_from_candidate(c: dict, total_time_seconds: int | None) -> CandidateRow:
    return CandidateRow(
        id=c["id"],
        invited_label=c.get("invited_label"),
        invited_label_email=c.get("invited_label_email"),
        candidate_name=c.get("candidate_name"),
        candidate_email=c.get("candidate_email"),
        created_at=c["created_at"],
        started_at=c.get("started_at"),
        submitted_at=c.get("submitted_at"),
        link_used=c.get("link_used", False),
        recommendation=c.get("recommendation"),
        manager_decision=c.get("manager_decision"),
        total_time_seconds=total_time_seconds,
    )


@router.get("/candidates", response_model=list[CandidateRow])
def list_candidates(_: dict = Depends(_require_manager)) -> list[CandidateRow]:
    rows = (
        get_supabase().table("candidates").select("*")
        .order("created_at", desc=True).execute()
    ).data or []
    out: list[CandidateRow] = []
    for c in rows:
        tts = None
        if c.get("submitted_at") and c.get("started_at"):
            from datetime import datetime
            tts = int(
                (datetime.fromisoformat(c["submitted_at"].replace("Z", "+00:00"))
                 - datetime.fromisoformat(c["started_at"].replace("Z", "+00:00"))).total_seconds()
            )
        out.append(_row_from_candidate(c, tts))
    return out


@router.get("/candidates/{cid}", response_model=CandidateDetail)
def candidate_detail(cid: str, _: dict = Depends(_require_manager)) -> CandidateDetail:
    candidate = (
        get_supabase().table("candidates").select("*").eq("id", cid).single().execute().data
    )
    if candidate is None:
        raise HTTPException(404, "Unknown candidate")

    decisions = (
        get_supabase().table("candidate_decisions")
        .select("*").eq("candidate_id", cid).order("pool").order("display_index").execute()
    ).data or []
    items = (
        get_supabase().table("test_items").select("*").execute()
    ).data or []
    items_by_id = {i["id"]: i for i in items}
    quiz = (
        get_supabase().table("candidate_quiz_answers")
        .select("is_correct").eq("candidate_id", cid).execute()
    ).data or []
    events = (
        get_supabase().table("candidate_events")
        .select("*").eq("candidate_id", cid).execute()
    ).data or []

    tab_switches = sum(1 for e in events if e["kind"] == "tab_blur")
    quiz_correct = sum(1 for q in quiz if q.get("is_correct"))

    steps: list[StepBreakdown] = []
    for pool in POOLS:
        step_decisions = [d for d in decisions if d["pool"] == pool]
        accuracy = (sum(1 for d in step_decisions if d["is_correct"]) / len(step_decisions)) if step_decisions else 0.0
        expected_duplicates = sum(
            1 for i in items
            if i["pool"] == pool and i.get("duplicate_of_item") is not None
        )
        dupes = [d for d in step_decisions if d["duplicate_of"] is not None]
        dupe_consistency = sum(
            1 for d in dupes
            if next((x for x in step_decisions if x["id"] == d["duplicate_of"]), {}).get("answer") == d["answer"]
        )
        median_dwell = None
        if step_decisions:
            ds = sorted(d["dwell_ms"] for d in step_decisions)
            median_dwell = ds[len(ds) // 2]
        # duration: step_start (intro_acked=true) → step_end
        intro = next((e for e in events if e["kind"] == "step_start" and (e.get("meta") or {}).get("pool") == pool and (e.get("meta") or {}).get("intro_acked")), None)
        end = next((e for e in events if e["kind"] == "step_end" and (e.get("meta") or {}).get("pool") == pool), None)
        duration = None
        if intro and end:
            from datetime import datetime
            duration = int(
                (datetime.fromisoformat(end["occurred_at"].replace("Z", "+00:00"))
                 - datetime.fromisoformat(intro["occurred_at"].replace("Z", "+00:00"))).total_seconds()
            )
        steps.append(StepBreakdown(
            pool=pool, accuracy=accuracy,
            duplicate_consistency=dupe_consistency,
            expected_duplicates=expected_duplicates,
            median_dwell_ms=median_dwell, duration_seconds=duration,
        ))

    free_text = [
        {
            "pool": d["pool"],
            "item_id": d["item_id"],
            "item_storage_path": items_by_id[d["item_id"]]["storage_path"],
            "justification": d["justification"],
        }
        for d in decisions if d.get("justification")
    ]

    tts = None
    if candidate.get("submitted_at") and candidate.get("started_at"):
        from datetime import datetime
        tts = int(
            (datetime.fromisoformat(candidate["submitted_at"].replace("Z", "+00:00"))
             - datetime.fromisoformat(candidate["started_at"].replace("Z", "+00:00"))).total_seconds()
        )

    return CandidateDetail(
        row=_row_from_candidate(candidate, tts),
        auto_fail_reasons=candidate.get("auto_fail_reasons") or [],
        quiz_correct=quiz_correct,
        quiz_total=len(quiz),
        tab_switches=tab_switches,
        steps=steps,
        free_text_justifications=free_text,
        decisions=[
            {
                "id": d["id"], "pool": d["pool"], "display_index": d["display_index"],
                "item_id": d["item_id"],
                "storage_path": items_by_id[d["item_id"]]["storage_path"],
                "reference_path": items_by_id[d["item_id"]].get("reference_path"),
                "answer": d["answer"], "is_correct": d["is_correct"],
                "dwell_ms": d["dwell_ms"], "is_duplicate": d["duplicate_of"] is not None,
                "justification": d.get("justification"),
            }
            for d in decisions
        ],
        manager_notes=candidate.get("manager_notes"),
    )


@router.patch("/candidates/{cid}")
def patch_candidate(cid: str, body: PatchCandidateRequest, _: dict = Depends(_require_manager)) -> dict:
    update: dict[str, Any] = {}
    if body.manager_decision is not None:
        update["manager_decision"] = body.manager_decision
    if body.manager_notes is not None:
        update["manager_notes"] = body.manager_notes
    if not update:
        return {"ok": True}
    get_supabase().table("candidates").update(update).eq("id", cid).execute()
    return {"ok": True}


@router.get("/items/{item_id}/signed-url")
def item_signed_url(item_id: str, _: dict = Depends(_require_manager)) -> dict:
    item = get_supabase().table("test_items").select("*").eq("id", item_id).single().execute().data
    if item is None:
        raise HTTPException(404, "Unknown item")
    return {"url": signed_url_for_item(item["pool"], item["storage_path"])}
