from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import math
import random
from typing import Iterable, Sequence

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState


WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "cold_start": {
        "weakness": 0.10,
        "new": 0.40,
        "srs": 0.00,
        "zpd": 0.20,
        "coverage": 0.25,
        "misconception": 0.05,
    },
    "warm": {
        "weakness": 0.30,
        "new": 0.20,
        "srs": 0.10,
        "zpd": 0.15,
        "coverage": 0.12,
        "misconception": 0.13,
    },
    "established": {
        "weakness": 0.25,
        "new": 0.10,
        "srs": 0.20,
        "zpd": 0.13,
        "coverage": 0.10,
        "misconception": 0.22,
    },
}

K_MODIFIER: dict[str, float] = {
    "MASTERED": 1.2,
    "LEARNED": 1.0,
    "DEVELOPING": 0.7,
    "CARELESS_OR_MISCONCEPTION": 0.5,
    "KNOWLEDGE_GAP": 1.0,
    "SIGNIFICANT_GAP": 1.2,
}

DEFAULT_TOPIC_SKILL = 2.5
DEFAULT_COGNITIVE_SKILL = 2.5
DEFAULT_PROCESSING_SKILL = 2.5


@dataclass(slots=True)
class ScoredQuestion:
    question: AdaptiveQuestionProfile
    priority: float
    components: dict[str, float]


def get_phase(student_state: AdaptiveStudentState) -> str:
    quizzes_completed = int(student_state.total_quizzes_completed)
    if quizzes_completed <= 2:
        return "cold_start"
    if quizzes_completed <= 8:
        return "warm"
    return "established"


def days_to_exam(
    student_state: AdaptiveStudentState,
    *,
    now: datetime | None = None,
) -> int | None:
    if student_state.exam_date is None:
        return None

    current_time = now or datetime.now(UTC)
    exam_date = student_state.exam_date
    if exam_date.tzinfo is None:
        current_time = current_time.replace(tzinfo=None)

    delta = exam_date - current_time
    return math.ceil(delta.total_seconds() / 86_400)


def apply_exam_modifier(weights: dict[str, float], days_to_exam_value: int | None) -> dict[str, float]:
    if days_to_exam_value is None or days_to_exam_value > 14:
        return dict(weights)

    adjusted = dict(weights)
    if days_to_exam_value <= 7:
        adjusted["weakness"] *= 1.5
        adjusted["srs"] *= 1.5
        adjusted["new"] *= 0.3
        adjusted["misconception"] *= 1.3
    else:
        adjusted["weakness"] *= 1.3
        adjusted["srs"] *= 1.2
        adjusted["new"] *= 0.6

    total = sum(adjusted.values())
    if total <= 0:
        return adjusted

    return {key: value / total for key, value in adjusted.items()}


def get_weight_profile(
    student_state: AdaptiveStudentState,
    *,
    now: datetime | None = None,
) -> dict[str, float]:
    phase = get_phase(student_state)
    weights = WEIGHT_PROFILES[phase]
    return apply_exam_modifier(weights, days_to_exam(student_state, now=now))


def get_candidates(
    course_questions: Sequence[AdaptiveQuestionProfile],
    *,
    current_session_question_ids: Iterable[str] | None = None,
    recently_correct_at_by_question: dict[str, datetime] | None = None,
    now: datetime | None = None,
) -> list[AdaptiveQuestionProfile]:
    current_session_question_ids = set(current_session_question_ids or ())
    recently_correct_at_by_question = recently_correct_at_by_question or {}
    current_time = now or datetime.now(UTC)

    candidates: list[AdaptiveQuestionProfile] = []
    for question in course_questions:
        if question.question_id in current_session_question_ids:
            continue

        last_correct_at = recently_correct_at_by_question.get(question.question_id)
        if last_correct_at is not None:
            if last_correct_at.tzinfo is None:
                elapsed = current_time.replace(tzinfo=None) - last_correct_at
            else:
                elapsed = current_time - last_correct_at
            if elapsed < timedelta(hours=24):
                continue

        candidates.append(question)

    return candidates


def weakness_score(
    question: AdaptiveQuestionProfile,
    attempts: Sequence,
) -> float:
    history = list(attempts)
    if not history:
        return 0.0

    wrong_attempts = [attempt for attempt in history if not getattr(attempt, "is_correct", False)]
    if not wrong_attempts:
        return 0.0

    total = len(history)
    error_rate = len(wrong_attempts) / total
    recency = 1.0

    timestamps = [
        getattr(attempt, "created_at", None)
        for attempt in wrong_attempts
        if getattr(attempt, "created_at", None) is not None
    ]
    last_wrong = max(timestamps, default=None)
    if last_wrong is not None:
        current_time = datetime.now(UTC)
        if getattr(last_wrong, "tzinfo", None) is None:
            current_time = current_time.replace(tzinfo=None)
        days_since_last_wrong = max(0.0, (current_time - last_wrong).total_seconds() / 86_400)
        recency = math.exp(-days_since_last_wrong / 7.0)

    return min(1.0, error_rate * recency)


def new_question_score(
    question: AdaptiveQuestionProfile,
    student_state: AdaptiveStudentState,
    attempted_question_ids: Iterable[str] | None = None,
) -> float:
    attempted_question_ids = set(attempted_question_ids or ())
    if question.question_id in attempted_question_ids:
        return 0.0

    topic_skill = student_state.topic_skills.get(question.topic_id, DEFAULT_TOPIC_SKILL)
    target = topic_skill + 0.5
    distance = abs(question.scaled_score - target)
    return max(0.1, 1.0 - distance / 4.0)


def srs_score(
    question: AdaptiveQuestionProfile,
    *,
    box: int | None = None,
    days_since_last_correct: int | None = None,
) -> float:
    if box is None:
        return 0.0
    if days_since_last_correct is None:
        return 0.0

    from src.domains.adaptive.srs import srs_interval_for_box

    interval = srs_interval_for_box(box)
    if days_since_last_correct < interval:
        return 0.0

    overdue_ratio = min(2.0, days_since_last_correct / max(interval, 1))
    return 0.5 + 0.5 * overdue_ratio


def zpd_score(question: AdaptiveQuestionProfile, student_state: AdaptiveStudentState) -> float:
    topic_skill = student_state.topic_skills.get(question.topic_id, DEFAULT_TOPIC_SKILL)
    sweet_spot = topic_skill + 0.5
    distance = abs(question.scaled_score - sweet_spot)
    return max(0.0, 1.0 - distance / 3.0)


def coverage_score(
    question: AdaptiveQuestionProfile,
    selected_so_far: Sequence[AdaptiveQuestionProfile],
    quiz_length: int,
) -> float:
    topic_count = sum(1 for item in selected_so_far if item.topic_id == question.topic_id)
    max_per_topic = max(1, math.ceil(quiz_length / 3))
    if topic_count >= max_per_topic:
        return -10.0
    return 1.0 - (topic_count / max_per_topic)


def misconception_score(question: AdaptiveQuestionProfile, student_state: AdaptiveStudentState) -> float:
    for flag in student_state.misconception_flags:
        if flag.get("topic_id") != question.topic_id:
            continue
        if flag.get("resolved"):
            continue
        if question.distractor_complexity is not None and question.distractor_complexity >= 1.2:
            return 1.5
        return 0.8
    return 0.0


def score_question(
    question: AdaptiveQuestionProfile,
    student_state: AdaptiveStudentState,
    *,
    selected_so_far: Sequence[AdaptiveQuestionProfile],
    quiz_length: int,
    attempts: Sequence = (),
    attempted_question_ids: Iterable[str] | None = None,
    box: int | None = None,
    days_since_last_correct: int | None = None,
) -> ScoredQuestion:
    weights = get_weight_profile(student_state)
    components = {
        "weakness": weakness_score(question, attempts),
        "new": new_question_score(question, student_state, attempted_question_ids),
        "srs": srs_score(question, box=box, days_since_last_correct=days_since_last_correct),
        "zpd": zpd_score(question, student_state),
        "coverage": coverage_score(question, selected_so_far, quiz_length),
        "misconception": misconception_score(question, student_state),
    }
    priority = sum(weights[name] * value for name, value in components.items())
    return ScoredQuestion(question=question, priority=priority, components=components)


def cold_start_selection(
    course_questions: Sequence[AdaptiveQuestionProfile],
    quiz_length: int,
    *,
    rng: random.Random | None = None,
) -> list[AdaptiveQuestionProfile]:
    rng = rng or random.Random()
    remaining = list(course_questions)
    grouped: dict[str, list[AdaptiveQuestionProfile]] = {}
    for question in remaining:
        grouped.setdefault(question.topic_id, []).append(question)

    selected: list[AdaptiveQuestionProfile] = []
    for topic_id in sorted(grouped):
        topic_questions = grouped[topic_id]
        easy = [question for question in topic_questions if question.band <= 2]
        pool = easy or topic_questions
        chosen = rng.choice(pool)
        if chosen not in selected:
            selected.append(chosen)
        if len(selected) >= quiz_length:
            return selected[:quiz_length]

    if len(selected) < quiz_length:
        pool = [question for question in remaining if question not in selected]
        easy = [question for question in pool if question.band <= 2]
        medium = [question for question in pool if question.band == 3]
        hard = [question for question in pool if question.band >= 4]

        remaining_slots = quiz_length - len(selected)
        easy_target = round(remaining_slots * 0.4)
        medium_target = round(remaining_slots * 0.4)
        hard_target = max(0, remaining_slots - easy_target - medium_target)
        for bucket, target in ((easy, easy_target), (medium, medium_target), (hard, hard_target)):
            if not bucket or target <= 0:
                continue
            take = min(target, len(bucket))
            selected.extend(rng.sample(bucket, take))

    return selected[:quiz_length]


def select_questions(
    course_questions: Sequence[AdaptiveQuestionProfile],
    student_state: AdaptiveStudentState,
    quiz_length: int,
    *,
    current_session_question_ids: Iterable[str] | None = None,
    recently_correct_at_by_question: dict[str, datetime] | None = None,
    attempts_by_question: dict[str, Sequence] | None = None,
    attempted_question_ids: Iterable[str] | None = None,
    srs_by_question: dict[str, object] | None = None,
    now: datetime | None = None,
    rng: random.Random | None = None,
) -> list[AdaptiveQuestionProfile]:
    rng = rng or random.Random()
    current_time = now or datetime.now(UTC)
    candidates = get_candidates(
        course_questions,
        current_session_question_ids=current_session_question_ids,
        recently_correct_at_by_question=recently_correct_at_by_question,
        now=current_time,
    )

    if not candidates:
        return []

    if get_phase(student_state) == "cold_start" and not attempts_by_question:
        return cold_start_selection(candidates, quiz_length, rng=rng)

    selected: list[AdaptiveQuestionProfile] = []
    remaining = list(candidates)
    attempts_by_question = attempts_by_question or {}
    attempted_question_ids = set(attempted_question_ids or ())
    srs_by_question = srs_by_question or {}

    while remaining and len(selected) < quiz_length:
        scored = []
        for question in remaining:
            srs_state = srs_by_question.get(question.question_id)
            box = getattr(srs_state, "box", None)
            last_correct_at = getattr(srs_state, "last_correct_at", None)
            days_since_last_correct = None
            if last_correct_at is not None:
                if last_correct_at.tzinfo is None:
                    elapsed = current_time.replace(tzinfo=None) - last_correct_at
                else:
                    elapsed = current_time - last_correct_at
                days_since_last_correct = max(0, elapsed.days)

            scored.append(
                score_question(
                    question,
                    student_state,
                    selected_so_far=selected,
                    quiz_length=quiz_length,
                    attempts=attempts_by_question.get(question.question_id, ()),
                    attempted_question_ids=attempted_question_ids,
                    box=box,
                    days_since_last_correct=days_since_last_correct,
                )
            )

        scored.sort(key=lambda item: item.priority, reverse=True)
        top_n = scored[:3]
        if not top_n:
            break

        total_priority = sum(item.priority for item in top_n)
        if total_priority <= 0:
            chosen = rng.choice([item.question for item in top_n])
        else:
            chosen = rng.choices(
                [item.question for item in top_n],
                weights=[max(item.priority, 0.0) for item in top_n],
                k=1,
            )[0]

        selected.append(chosen)
        attempted_question_ids.add(chosen.question_id)
        remaining = [question for question in remaining if question.question_id != chosen.question_id]

    return selected[:quiz_length]
