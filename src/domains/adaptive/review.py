from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from src.domains.adaptive.models import AdaptiveQuestionProfile


@dataclass(slots=True)
class ReviewFinding:
    question_id: int
    flag_type: str
    reason: str
    suggestion: str
    metadata: dict


def analyze_empirical_difficulty(
    question: AdaptiveQuestionProfile,
    attempts: Sequence,
    *,
    question_id: int,
) -> ReviewFinding | None:
    if len(attempts) < 10:
        return None

    correct = sum(1 for attempt in attempts if getattr(attempt, "is_correct", False))
    success_rate = correct / len(attempts)
    empirical_difficulty = 1.0 + (1.0 - success_rate) * 4.0
    divergence = abs(empirical_difficulty - question.scaled_score)

    if divergence <= 1.0:
        return None

    return ReviewFinding(
        question_id=question_id,
        flag_type="difficulty_divergence",
        reason=(
            f"Scored difficulty {question.scaled_score:.1f} diverges from empirical "
            f"difficulty {empirical_difficulty:.1f} by {divergence:.1f}"
        ),
        suggestion="Re-evaluate scoring parameters or question quality.",
        metadata={
            "scaled_score": question.scaled_score,
            "empirical_difficulty": empirical_difficulty,
            "success_rate": success_rate,
            "divergence": divergence,
        },
    )


def analyze_distractor_patterns(
    question: AdaptiveQuestionProfile,
    attempts: Sequence,
    *,
    question_id: int,
) -> ReviewFinding | None:
    wrong_attempts = [attempt for attempt in attempts if not getattr(attempt, "is_correct", False)]
    if len(wrong_attempts) < 15:
        return None

    distractor_values = [
        getattr(attempt, "selected_option_id", None)
        for attempt in wrong_attempts
        if getattr(attempt, "selected_option_id", None) is not None
    ]
    if not distractor_values:
        return None

    counts = Counter(distractor_values)
    total_wrong = len(distractor_values)
    option_id, count = counts.most_common(1)[0]
    ratio = count / total_wrong
    if ratio <= 0.60:
        return None

    return ReviewFinding(
        question_id=question_id,
        flag_type="distractor_bias",
        reason=(
            f"Distractor {option_id!r} selected by {count}/{total_wrong} "
            f"({ratio:.0%}) of wrong answers"
        ),
        suggestion="Add a targeted explanation or revise the distractors.",
        metadata={
            "selected_option_id": option_id,
            "count": count,
            "total_wrong": total_wrong,
            "ratio": ratio,
        },
    )


def analyze_time_allocation(
    question: AdaptiveQuestionProfile,
    attempts: Sequence,
    *,
    question_id: int,
) -> ReviewFinding | None:
    times = [
        getattr(attempt, "time_taken_seconds", None)
        for attempt in attempts
        if getattr(attempt, "time_taken_seconds", None) is not None
    ]
    if len(times) < 15:
        return None

    times = sorted(float(value) for value in times)
    median_time = times[len(times) // 2]
    current_limit = _calculate_time_limit(question)

    if median_time < current_limit * 0.4:
        return ReviewFinding(
            question_id=question_id,
            flag_type="time_limit_review",
            reason=(
                f"Median completion time {median_time:.1f}s is less than 40% of "
                f"the current limit {current_limit}s"
            ),
            suggestion="Question may be over-timed or easier than scored.",
            metadata={
                "median_time": median_time,
                "current_limit": current_limit,
                "ratio": median_time / current_limit if current_limit else None,
            },
        )

    if sum(1 for value in times if value >= current_limit * 0.95) / len(times) > 0.30:
        return ReviewFinding(
            question_id=question_id,
            flag_type="time_limit_review",
            reason="More than 30% of students used at least 95% of the time limit",
            suggestion="Question may be under-timed or harder than scored.",
            metadata={
                "median_time": median_time,
                "current_limit": current_limit,
            },
        )

    return None


def _calculate_time_limit(question: AdaptiveQuestionProfile) -> int:
    base_time = 45
    if question.scaled_score <= 1.5:
        multiplier = 1.0
    elif question.scaled_score <= 3.0:
        multiplier = 1.5
    elif question.scaled_score <= 4.5:
        multiplier = 2.0
    else:
        multiplier = 2.5

    if question.processing_complexity is not None and question.processing_complexity >= 1.4:
        multiplier += 0.25
    if question.processing_complexity is not None and question.processing_complexity >= 1.5:
        multiplier += 0.25
    if question.note_reference is not None and question.note_reference >= 1.5:
        multiplier += 0.15

    return round(base_time * multiplier)
