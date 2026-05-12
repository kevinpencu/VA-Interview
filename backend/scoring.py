"""Pure scoring logic: recommendation + auto_fail_reasons from raw stats."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from config import (
    POOLS,
    QUIZ_PASS_THRESHOLD,
    STEP_ACCURACY_BORDERLINE_FLOOR,
    STEP_ACCURACY_FAIL_FLOOR,
    TAB_SWITCH_BORDERLINE_THRESHOLD,
)


Recommendation = Literal["pass", "borderline", "fail"]


@dataclass(frozen=True)
class StepStats:
    accuracy: float                # correct / 30
    duplicate_consistency: int     # 0..expected_duplicates
    expected_duplicates: int       # how many tracked dupes exist for the pool


@dataclass(frozen=True)
class ScoringInput:
    quiz_score: int                # 0..QUIZ_QUESTION_COUNT
    tab_switches: int
    tiktok: StepStats
    nano_banana: StepStats
    kling: StepStats

    def step(self, name: str) -> StepStats:
        return getattr(self, name)


def compute_recommendation(inp: ScoringInput) -> tuple[Recommendation, list[str]]:
    """Return (recommendation, [auto_fail_reasons]).

    Order of evaluation:
    1. Hard fail rules. If any fire → 'fail' with fail-reasons only.
    2. Borderline rules. If any fire → 'borderline' with all reasons.
    3. Otherwise 'pass' with empty reasons.
    """
    fail_reasons: list[str] = []

    if inp.quiz_score < QUIZ_PASS_THRESHOLD:
        fail_reasons.append("failed_quiz")

    for pool in POOLS:
        s = inp.step(pool)
        if s.duplicate_consistency < s.expected_duplicates:
            fail_reasons.append(f"inconsistent_duplicate_{pool}")
        if s.accuracy < STEP_ACCURACY_FAIL_FLOOR:
            fail_reasons.append(f"below_floor_{pool}")

    if fail_reasons:
        return "fail", fail_reasons

    borderline_reasons: list[str] = []
    for pool in POOLS:
        s = inp.step(pool)
        if s.accuracy < STEP_ACCURACY_BORDERLINE_FLOOR:
            borderline_reasons.append(f"weak_step_{pool}")
    if inp.tab_switches > TAB_SWITCH_BORDERLINE_THRESHOLD:
        borderline_reasons.append("high_tab_switching")

    if borderline_reasons:
        return "borderline", borderline_reasons

    return "pass", []
