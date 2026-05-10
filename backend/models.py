"""Pydantic v2 schemas for API requests/responses."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Pool = Literal["tiktok", "nano_banana", "kling"]
Recommendation = Literal["pass", "borderline", "fail"]
ManagerDecision = Literal["hired", "rejected"]
EventKind = Literal[
    "tab_blur", "tab_focus", "step_start", "step_end",
    "tutorial_view", "quiz_start", "quiz_end", "session_start",
]


# ============================================================
# Candidate-side requests
# ============================================================

class StartRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr


class QuizRequest(BaseModel):
    answers: list[int] = Field(min_length=5, max_length=5)


class DecisionRequest(BaseModel):
    item_id: str
    answer: bool
    dwell_ms: int = Field(ge=0)
    shown_at: datetime


class JustificationRequest(BaseModel):
    decision_id: str
    justification: str = Field(min_length=1, max_length=2000)


class EventRequest(BaseModel):
    kind: EventKind
    meta: dict = Field(default_factory=dict)


# ============================================================
# Candidate-side responses
# ============================================================

class StateResponseItem(BaseModel):
    """The next item to show, when state is step_<n>_in_progress."""
    id: str
    storage_url: str       # signed URL for the media file
    pool: Pool
    display_index: int     # 0..29


class StateResponse(BaseModel):
    state: Literal[
        "needs_name", "needs_tutorial", "needs_quiz",
        "step_tiktok_intro", "step_tiktok_in_progress",
        "step_nano_banana_intro", "step_nano_banana_in_progress",
        "step_kling_intro", "step_kling_in_progress",
        "submitted", "invalid", "session_in_use",
    ]
    progress_in_step: int = 0       # number of decisions already submitted in current step
    next_item: StateResponseItem | None = None


class DecisionResponseNext(BaseModel):
    item: StateResponseItem | None = None
    step_complete: bool = False
    test_complete: bool = False


class DecisionResponse(BaseModel):
    decision_id: str
    needs_justification: bool
    next: DecisionResponseNext


class QuizResponse(BaseModel):
    passed: bool
    score: int        # 0..5


# ============================================================
# Manager-side requests
# ============================================================

class CreateInviteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr


class CreateInviteResponse(BaseModel):
    candidate_id: str
    token: str
    url: str


class PatchCandidateRequest(BaseModel):
    manager_decision: ManagerDecision | None = None
    manager_notes: str | None = None


# ============================================================
# Manager-side responses
# ============================================================

class CandidateRow(BaseModel):
    id: str
    invited_label: str | None
    invited_label_email: str | None
    candidate_name: str | None
    candidate_email: str | None
    created_at: datetime
    started_at: datetime | None
    submitted_at: datetime | None
    link_used: bool
    recommendation: Recommendation | None
    manager_decision: ManagerDecision | None
    total_time_seconds: int | None


class StepBreakdown(BaseModel):
    pool: Pool
    accuracy: float
    obvious_bad_caught: int
    obvious_good_caught: int
    duplicate_consistency: int
    median_dwell_ms: int | None
    duration_seconds: int | None


class CandidateDetail(BaseModel):
    row: CandidateRow
    auto_fail_reasons: list[str]
    quiz_correct: int
    quiz_total: int
    tab_switches: int
    steps: list[StepBreakdown]
    free_text_justifications: list[dict]   # [{pool, item_id, item_storage_path, justification}]
    decisions: list[dict]                  # full per-item record for the expandable view
    manager_notes: str | None
