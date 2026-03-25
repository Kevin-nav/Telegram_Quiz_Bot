from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState
from src.domains.adaptive.selection import (
    WEIGHT_PROFILES,
    apply_exam_modifier,
    cold_start_selection,
    coverage_score,
    get_candidates,
    get_phase,
    misconception_score,
    new_question_score,
    score_question,
    select_questions,
    weakness_score,
    zpd_score,
)


@dataclass(slots=True)
class Attempt:
    is_correct: bool
    created_at: datetime


class DeterministicRng:
    def __init__(self):
        self.choices_calls = []

    def choice(self, population):
        return population[0]

    def sample(self, population, k):
        return list(population[:k])

    def choices(self, population, weights=None, k=1):
        self.choices_calls.append(
            {
                "population": [item.question_id for item in population],
                "weights": list(weights or []),
                "k": k,
            }
        )
        return [population[-1]]


def make_question(**overrides):
    payload = {
        "question_id": "q1",
        "topic_id": "topic-a",
        "scaled_score": 2.0,
        "band": 2,
        "cognitive_level": "Understanding",
        "processing_complexity": 1.0,
        "distractor_complexity": 1.0,
        "note_reference": 1.0,
        "question_type": "MCQ",
        "option_count": 4,
        "has_latex": False,
        "arrangement_hash": None,
        "config_index": None,
    }
    payload.update(overrides)
    return AdaptiveQuestionProfile(**payload)


def test_get_phase_uses_quiz_count_thresholds():
    assert get_phase(AdaptiveStudentState(total_quizzes_completed=0)) == "cold_start"
    assert get_phase(AdaptiveStudentState(total_quizzes_completed=5)) == "warm"
    assert get_phase(AdaptiveStudentState(total_quizzes_completed=9)) == "established"


def test_apply_exam_modifier_rebalances_weights_and_normalizes():
    modified = apply_exam_modifier(WEIGHT_PROFILES["established"], 6)

    assert round(sum(modified.values()), 10) == 1.0
    assert modified["weakness"] > WEIGHT_PROFILES["established"]["weakness"]
    assert modified["new"] < WEIGHT_PROFILES["established"]["new"]


def test_component_scores_reflect_history_skill_and_flags():
    student = AdaptiveStudentState(
        topic_skills={"topic-a": 2.5},
        misconception_flags=[{"topic_id": "topic-a", "resolved": False}],
    )
    question = make_question(scaled_score=3.0, distractor_complexity=1.3)
    attempts = [
        Attempt(is_correct=False, created_at=datetime.now(UTC) - timedelta(days=1)),
        Attempt(is_correct=True, created_at=datetime.now(UTC) - timedelta(days=2)),
    ]

    assert weakness_score(question, attempts) > 0.0
    assert new_question_score(question, student, attempted_question_ids=()) > 0.0
    assert zpd_score(question, student) > 0.0
    assert coverage_score(question, [], 3) == 1.0
    assert misconception_score(question, student) == 1.5
    scored = score_question(
        question,
        student,
        selected_so_far=[],
        quiz_length=3,
        attempts=attempts,
    )
    assert scored.priority > 0.0
    assert scored.components["weakness"] > 0.0


def test_get_candidates_filters_session_repeats_and_recent_correct_questions():
    now = datetime.now(UTC)
    first = make_question(question_id="q1")
    second = make_question(question_id="q2")

    candidates = get_candidates(
        [first, second],
        current_session_question_ids={"q1"},
        recently_correct_at_by_question={"q2": now - timedelta(hours=1)},
        now=now,
    )

    assert candidates == []


def test_cold_start_selection_prefers_easy_questions_by_topic():
    questions = [
        make_question(question_id="q1", topic_id="topic-a", band=1),
        make_question(question_id="q2", topic_id="topic-a", band=4),
        make_question(question_id="q3", topic_id="topic-b", band=2),
        make_question(question_id="q4", topic_id="topic-c", band=3),
    ]

    selected = cold_start_selection(questions, 3, rng=DeterministicRng())

    assert len(selected) == 3
    assert selected[0].topic_id == "topic-a"
    assert selected[1].topic_id == "topic-b"


def test_select_questions_uses_top_three_weighted_random_choice():
    questions = [
        make_question(question_id="q1", scaled_score=2.5),
        make_question(question_id="q2", scaled_score=2.6),
        make_question(question_id="q3", scaled_score=3.5),
        make_question(question_id="q4", scaled_score=4.5),
    ]
    student = AdaptiveStudentState(
        total_quizzes_completed=10,
        topic_skills={"topic-a": 2.5},
    )
    attempts_by_question = {
        "q1": [Attempt(is_correct=False, created_at=datetime.now(UTC) - timedelta(days=1))],
        "q2": [],
        "q3": [],
        "q4": [],
    }
    rng = DeterministicRng()

    selected = select_questions(
        questions,
        student,
        2,
        attempts_by_question=attempts_by_question,
        rng=rng,
    )

    assert len(selected) == 2
    assert rng.choices_calls
    assert all(question_id in {"q1", "q2", "q3"} for question_id in rng.choices_calls[0]["population"])
    assert selected[0].question_id == "q3"
