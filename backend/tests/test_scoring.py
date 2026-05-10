"""Tests for scoring.compute_recommendation."""
from __future__ import annotations

from scoring import StepStats, ScoringInput, compute_recommendation


def _step(
    accuracy: float = 1.0,
    obvious_bad_caught: int = 4,
    obvious_good_caught: int = 4,
    duplicate_consistency: int = 2,
) -> StepStats:
    return StepStats(
        accuracy=accuracy,
        obvious_bad_caught=obvious_bad_caught,
        obvious_good_caught=obvious_good_caught,
        duplicate_consistency=duplicate_consistency,
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


def test_missed_obvious_bad_is_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(obvious_bad_caught=3)))
    assert rec == "fail"
    assert "missed_obvious_bad_tiktok" in reasons


def test_missed_obvious_bad_in_kling_is_fail():
    rec, reasons = compute_recommendation(_input(kling=_step(obvious_bad_caught=2)))
    assert rec == "fail"
    assert "missed_obvious_bad_kling" in reasons


def test_dupe_inconsistency_is_fail():
    rec, reasons = compute_recommendation(_input(nano_banana=_step(duplicate_consistency=1)))
    assert rec == "fail"
    assert "inconsistent_duplicate_nano_banana" in reasons


def test_below_floor_accuracy_is_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(accuracy=0.69)))
    assert rec == "fail"
    assert "below_floor_tiktok" in reasons


def test_70_percent_is_not_fail():
    rec, reasons = compute_recommendation(_input(tiktok=_step(accuracy=0.70)))
    # 0.70 is the floor — ≥ 0.70 is not below floor. But < 0.80 is borderline.
    assert rec == "borderline"
    assert "weak_step_tiktok" in reasons


def test_rejected_obvious_good_is_borderline():
    rec, reasons = compute_recommendation(_input(kling=_step(obvious_good_caught=3)))
    assert rec == "borderline"
    assert "rejected_obvious_good_kling" in reasons


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
        kling=_step(obvious_good_caught=2),              # borderline
    ))
    assert rec == "fail"
    assert "failed_quiz" in reasons
    # borderline reasons not added when overall is fail
    assert all(not r.startswith("rejected_obvious_good") for r in reasons)


def test_multiple_fail_reasons_all_recorded():
    rec, reasons = compute_recommendation(_input(
        quiz_score=3,
        tiktok=_step(obvious_bad_caught=3),
        kling=_step(accuracy=0.5),
    ))
    assert rec == "fail"
    assert "failed_quiz" in reasons
    assert "missed_obvious_bad_tiktok" in reasons
    assert "below_floor_kling" in reasons
