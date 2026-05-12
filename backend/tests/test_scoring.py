"""Tests for scoring.compute_recommendation."""
from __future__ import annotations

from scoring import StepStats, ScoringInput, compute_recommendation


def _step(
    accuracy: float = 1.0,
    duplicate_consistency: int = 0,
    expected_duplicates: int = 0,
) -> StepStats:
    return StepStats(
        accuracy=accuracy,
        duplicate_consistency=duplicate_consistency,
        expected_duplicates=expected_duplicates,
    )


def _input(
    quiz_score: int = 5,
    tab_switches: int = 0,
    tiktok: StepStats | None = None,
    nano_banana: StepStats | None = None,
    kling: StepStats | None = None,
) -> ScoringInput:
    return ScoringInput(
        quiz_score=quiz_score,
        tab_switches=tab_switches,
        tiktok=tiktok or _step(),
        nano_banana=nano_banana or _step(),
        kling=kling or _step(),
    )


def test_perfect_candidate_passes():
    rec, reasons = compute_recommendation(_input())
    assert rec == "pass"
    assert reasons == []


def test_failed_quiz_is_fail():
    rec, reasons = compute_recommendation(_input(quiz_score=3))
    assert rec == "fail"
    assert "failed_quiz" in reasons


def test_dupe_inconsistency_is_fail():
    rec, reasons = compute_recommendation(_input(
        nano_banana=_step(expected_duplicates=1, duplicate_consistency=0),
    ))
    assert rec == "fail"
    assert "inconsistent_duplicate_nano_banana" in reasons


def test_zero_dupes_is_not_fail():
    rec, reasons = compute_recommendation(_input(
        tiktok=_step(expected_duplicates=0, duplicate_consistency=0),
        nano_banana=_step(expected_duplicates=0, duplicate_consistency=0),
        kling=_step(expected_duplicates=0, duplicate_consistency=0),
    ))
    assert rec == "pass"
    assert reasons == []


def test_below_floor_accuracy_is_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(accuracy=0.69)))
    assert rec == "fail"
    assert "below_floor_tiktok" in reasons


def test_70_percent_is_not_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(accuracy=0.70)))
    # 0.70 is the floor — ≥ 0.70 is not below floor. But < 0.80 is borderline.
    assert rec == "borderline"
    assert "weak_step_tiktok" in reasons


def test_high_tab_switches_is_borderline():
    rec, reasons = compute_recommendation(_input(tab_switches=6))
    assert rec == "borderline"
    assert "high_tab_switching" in reasons


def test_5_tab_switches_is_not_borderline():
    rec, reasons = compute_recommendation(_input(tab_switches=5))
    assert rec == "pass"
    assert reasons == []


def test_fail_takes_precedence_over_borderline():
    rec, reasons = compute_recommendation(_input(
        quiz_score=3,                                    # fail
        kling=_step(accuracy=0.75),                      # borderline (weak_step)
    ))
    assert rec == "fail"
    assert "failed_quiz" in reasons
    # borderline reasons not added when overall is fail
    assert all(not r.startswith("weak_step") for r in reasons)


def test_multiple_fail_reasons_all_recorded():
    rec, reasons = compute_recommendation(_input(
        quiz_score=3,
        tiktok=_step(expected_duplicates=1, duplicate_consistency=0),
        kling=_step(accuracy=0.5),
    ))
    assert rec == "fail"
    assert "failed_quiz" in reasons
    assert "inconsistent_duplicate_tiktok" in reasons
    assert "below_floor_kling" in reasons
