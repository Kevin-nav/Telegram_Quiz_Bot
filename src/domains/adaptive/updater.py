from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import math
from typing import Sequence

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState
from src.domains.adaptive.selection import K_MODIFIER, get_phase
from src.domains.adaptive.timing import classify_attempt_time


BASE_TOPIC_K = 0.5
BASE_COGNITIVE_K = 0.3
BASE_PROCESSING_K = 0.3
BASE_OVERALL_K = 0.2


@dataclass(slots=True)
class AdaptiveUpdateResult:
    student_state: AdaptiveStudentState
    classification: str
    effective_k: float
    topic_id: str
    topic_skill_before: float
    topic_skill_after: float
    overall_skill_before: float
    overall_skill_after: float
    cognitive_updates: dict[str, tuple[float, float]] = field(default_factory=dict)
    processing_updates: dict[str, tuple[float, float]] = field(default_factory=dict)
    misconception_added: bool = False
    misconception_resolved: bool = False
    decayed_topics: dict[str, tuple[float, float]] = field(default_factory=dict)


def clamp(value: float, minimum: float = 1.0, maximum: float = 5.0) -> float:
    return max(minimum, min(maximum, value))


def elo_expected(skill: float, difficulty: float) -> float:
    return 1.0 / (1.0 + math.exp(difficulty - skill))


def update_scalar_skill(
    skill: float,
    difficulty: float,
    actual: float,
    *,
    k_factor: float,
) -> float:
    expected = elo_expected(skill, difficulty)
    updated = skill + k_factor * (actual - expected)
    return clamp(updated)


def classification_k_modifier(classification: str) -> float:
    return K_MODIFIER[classification]


def classify_attempt(
    *,
    is_correct: bool,
    time_taken_seconds: float | None,
    time_allocated_seconds: int | None,
) -> str:
    return classify_attempt_time(
        is_correct=is_correct,
        time_taken_seconds=time_taken_seconds,
        time_allocated_seconds=time_allocated_seconds,
    )


def effective_k(base_k: float, classification: str) -> float:
    return base_k * classification_k_modifier(classification)


def recalculate_phase(student_state: AdaptiveStudentState) -> str:
    phase = get_phase(student_state)
    student_state.phase = phase  # type: ignore[assignment]
    return phase


def _topic_decay_amount(days_inactive: int) -> float:
    if days_inactive <= 3:
        return 0.0
    decay = 0.02 * (days_inactive - 3)
    return min(decay, 0.5)


def apply_lazy_topic_decay(
    student_state: AdaptiveStudentState,
    topic_id: str,
    *,
    last_attempt_at: datetime | None = None,
    now: datetime | None = None,
) -> tuple[float, float]:
    current_skill = student_state.topic_skills.get(topic_id, 2.5)
    if last_attempt_at is None:
        return current_skill, current_skill

    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is not None:
        current_time = current_time.astimezone(UTC).replace(tzinfo=None)
    if last_attempt_at.tzinfo is not None:
        last_attempt_at = last_attempt_at.astimezone(UTC).replace(tzinfo=None)

    days_inactive = max(0, (current_time - last_attempt_at).days)
    decay = _topic_decay_amount(days_inactive)
    if decay <= 0:
        return current_skill, current_skill

    decayed_skill = clamp(current_skill - decay)
    student_state.topic_skills[topic_id] = decayed_skill
    return current_skill, decayed_skill


def _update_dimension(
    current_value: float,
    difficulty: float,
    actual: float,
    *,
    base_k: float,
    classification: str,
) -> float:
    return update_scalar_skill(
        current_value,
        difficulty,
        actual,
        k_factor=effective_k(base_k, classification),
    )


def _maybe_log_misconception(
    student_state: AdaptiveStudentState,
    question: AdaptiveQuestionProfile,
    *,
    classification: str,
    selected_distractor: str | None = None,
) -> bool:
    if question.question_type != "MCQ":
        return False
    if classification not in {
        "CARELESS_OR_MISCONCEPTION",
        "KNOWLEDGE_GAP",
        "SIGNIFICANT_GAP",
    }:
        return False

    if question.distractor_complexity is None or question.distractor_complexity < 1.2:
        return False

    for flag in student_state.misconception_flags:
        if (
            flag.get("topic_id") == question.topic_id
            and flag.get("question_id") == question.question_id
            and not flag.get("resolved", False)
        ):
            flag["times_selected"] = int(flag.get("times_selected", 0)) + 1
            if selected_distractor is not None:
                flag["selected_distractor"] = selected_distractor
            return False

    student_state.misconception_flags.append(
        {
            "topic_id": question.topic_id,
            "question_id": question.question_id,
            "selected_distractor": selected_distractor,
            "times_selected": 1,
            "resolved": False,
        }
    )
    return True


def resolve_misconception_flags(
    student_state: AdaptiveStudentState,
    question: AdaptiveQuestionProfile,
    attempts: Sequence,
) -> bool:
    correct_arrangements = {
        getattr(attempt, "arrangement_hash", None)
        for attempt in attempts
        if getattr(attempt, "is_correct", False)
    }
    correct_arrangements.discard(None)

    if len(correct_arrangements) < 2:
        return False

    resolved = False
    for flag in student_state.misconception_flags:
        if (
            flag.get("topic_id") == question.topic_id
            and flag.get("question_id") == question.question_id
            and not flag.get("resolved", False)
        ):
            flag["resolved"] = True
            resolved = True
    return resolved


def apply_attempt_update(
    student_state: AdaptiveStudentState,
    question: AdaptiveQuestionProfile,
    *,
    is_correct: bool,
    time_taken_seconds: float | None = None,
    time_allocated_seconds: int | None = None,
    selected_distractor: str | None = None,
    attempts_for_question: Sequence | None = None,
    processing_target: str | None = None,
    now: datetime | None = None,
) -> AdaptiveUpdateResult:
    classification = classify_attempt(
        is_correct=is_correct,
        time_taken_seconds=time_taken_seconds,
        time_allocated_seconds=time_allocated_seconds,
    )
    actual = 1.0 if is_correct else 0.0
    modifier = classification_k_modifier(classification)

    topic_skill_before = student_state.topic_skills.get(question.topic_id, 2.5)
    overall_before = student_state.overall_skill

    topic_skill_after = _update_dimension(
        topic_skill_before,
        question.scaled_score,
        actual,
        base_k=BASE_TOPIC_K,
        classification=classification,
    )
    overall_after = _update_dimension(
        overall_before,
        question.scaled_score,
        actual,
        base_k=BASE_OVERALL_K,
        classification=classification,
    )

    student_state.topic_skills[question.topic_id] = topic_skill_after
    student_state.overall_skill = overall_after

    cognitive_updates: dict[str, tuple[float, float]] = {}
    if question.cognitive_level:
        current = student_state.cognitive_profile.get(question.cognitive_level, 2.5)
        updated = _update_dimension(
            current,
            question.scaled_score,
            actual,
            base_k=BASE_COGNITIVE_K,
            classification=classification,
        )
        student_state.cognitive_profile[question.cognitive_level] = updated
        cognitive_updates[question.cognitive_level] = (current, updated)

    processing_updates: dict[str, tuple[float, float]] = {}
    if processing_target:
        current = student_state.processing_profile.get(processing_target, 2.5)
        updated = _update_dimension(
            current,
            question.scaled_score,
            actual,
            base_k=BASE_PROCESSING_K,
            classification=classification,
        )
        student_state.processing_profile[processing_target] = updated
        processing_updates[processing_target] = (current, updated)

    misconception_added = _maybe_log_misconception(
        student_state,
        question,
        classification=classification,
        selected_distractor=selected_distractor,
    )
    misconception_resolved = False
    if is_correct and attempts_for_question is not None:
        misconception_resolved = resolve_misconception_flags(
            student_state,
            question,
            attempts_for_question,
        )

    student_state.total_attempts += 1
    recalculate_phase(student_state)

    return AdaptiveUpdateResult(
        student_state=student_state,
        classification=classification,
        effective_k=BASE_TOPIC_K * modifier,
        topic_id=question.topic_id,
        topic_skill_before=topic_skill_before,
        topic_skill_after=topic_skill_after,
        overall_skill_before=overall_before,
        overall_skill_after=overall_after,
        cognitive_updates=cognitive_updates,
        processing_updates=processing_updates,
        misconception_added=misconception_added,
        misconception_resolved=misconception_resolved,
    )


def get_question_delta_skill(
    student_state: AdaptiveStudentState,
    question: AdaptiveQuestionProfile,
    *,
    is_correct: bool,
    time_taken_seconds: float | None = None,
    time_allocated_seconds: int | None = None,
) -> float:
    classification = classify_attempt(
        is_correct=is_correct,
        time_taken_seconds=time_taken_seconds,
        time_allocated_seconds=time_allocated_seconds,
    )
    return effective_k(BASE_TOPIC_K, classification)
