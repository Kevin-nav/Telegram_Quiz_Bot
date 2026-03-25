from __future__ import annotations

from src.domains.adaptive.models import AdaptiveQuestionProfile


BASE_TIME_SECONDS = 45
ATTEMPT_CLASSIFICATIONS = {
    "MASTERED",
    "LEARNED",
    "DEVELOPING",
    "CARELESS_OR_MISCONCEPTION",
    "KNOWLEDGE_GAP",
    "SIGNIFICANT_GAP",
}


def time_ratio(time_taken_seconds: float | None, time_allocated_seconds: int | None) -> float | None:
    if time_taken_seconds is None or time_allocated_seconds in (None, 0):
        return None
    return float(time_taken_seconds) / float(time_allocated_seconds)


def classify_attempt_time(
    *, is_correct: bool, time_taken_seconds: float | None, time_allocated_seconds: int | None
) -> str:
    ratio = time_ratio(time_taken_seconds, time_allocated_seconds)
    if ratio is None:
        return "LEARNED" if is_correct else "KNOWLEDGE_GAP"

    if is_correct:
        if ratio < 0.5:
            return "MASTERED"
        if ratio < 0.85:
            return "LEARNED"
        return "DEVELOPING"

    if ratio < 0.5:
        return "CARELESS_OR_MISCONCEPTION"
    if ratio < 0.85:
        return "KNOWLEDGE_GAP"
    return "SIGNIFICANT_GAP"


def calculate_question_time_limit(question: AdaptiveQuestionProfile) -> int:
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

    return round(BASE_TIME_SECONDS * multiplier)
