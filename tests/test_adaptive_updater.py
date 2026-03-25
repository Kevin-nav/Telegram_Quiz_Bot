from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState, AttemptRecord
from src.domains.adaptive.updater import (
    AdaptiveUpdateResult,
    apply_attempt_update,
    apply_lazy_topic_decay,
    classification_k_modifier,
    effective_k,
    elo_expected,
    recalculate_phase,
    resolve_misconception_flags,
    update_scalar_skill,
)


def make_student(**overrides):
    student = AdaptiveStudentState(
        overall_skill=2.5,
        topic_skills={"topic-1": 2.5},
        cognitive_profile={"Understanding": 2.5},
        processing_profile={"symbolic": 2.5},
        misconception_flags=[],
        total_quizzes_completed=0,
        total_attempts=0,
    )
    for key, value in overrides.items():
        setattr(student, key, value)
    return student


def make_question(**overrides):
    question = AdaptiveQuestionProfile(
        question_id="q-1",
        topic_id="topic-1",
        scaled_score=3.0,
        band=3,
        cognitive_level="Understanding",
        processing_complexity=1.5,
        distractor_complexity=1.6,
        note_reference=1.5,
    )
    for key, value in overrides.items():
        setattr(question, key, value)
    return question


def test_elo_helpers_move_toward_expected_direction():
    expected = elo_expected(2.5, 3.5)
    updated = update_scalar_skill(2.5, 3.5, 1.0, k_factor=0.5)

    assert 0.0 < expected < 1.0
    assert updated > 2.5
    assert classification_k_modifier("MASTERED") == 1.2
    assert effective_k(0.5, "MASTERED") == 0.6


def test_apply_attempt_update_improves_matching_skills_on_mastered_attempt():
    student = make_student()
    question = make_question()

    result = apply_attempt_update(
        student,
        question,
        is_correct=True,
        time_taken_seconds=10,
        time_allocated_seconds=30,
        processing_target="symbolic",
    )

    assert isinstance(result, AdaptiveUpdateResult)
    assert result.classification == "MASTERED"
    assert result.topic_skill_after > result.topic_skill_before
    assert result.overall_skill_after > result.overall_skill_before
    assert student.cognitive_profile["Understanding"] > 2.5
    assert student.processing_profile["symbolic"] > 2.5
    assert student.total_attempts == 1


def test_apply_attempt_update_logs_misconception_on_wrong_mcq():
    student = make_student()
    question = make_question()

    result = apply_attempt_update(
        student,
        question,
        is_correct=False,
        time_taken_seconds=28,
        time_allocated_seconds=30,
        selected_distractor="option_a",
    )

    assert result.classification == "SIGNIFICANT_GAP"
    assert result.misconception_added is True
    assert len(student.misconception_flags) == 1
    assert student.misconception_flags[0]["selected_distractor"] == "option_a"


def test_resolve_misconception_flags_requires_two_correct_arrangements():
    student = make_student(
        misconception_flags=[
            {
                "topic_id": "topic-1",
                "question_id": "q-1",
                "selected_distractor": "option_a",
                "times_selected": 1,
                "resolved": False,
            }
        ]
    )
    question = make_question()
    attempts = [
        AttemptRecord(is_correct=True, arrangement_hash="A-B-C-D"),
        AttemptRecord(is_correct=True, arrangement_hash="D-C-B-A"),
    ]

    resolved = resolve_misconception_flags(student, question, attempts)

    assert resolved is True
    assert student.misconception_flags[0]["resolved"] is True


def test_phase_recalculation_tracks_quiz_count():
    student = make_student(total_quizzes_completed=9)

    assert recalculate_phase(student) == "established"
    assert student.phase == "established"


def test_apply_lazy_topic_decay_reduces_stale_topic_skill():
    student = make_student(topic_skills={"topic-1": 3.5})
    last_attempt_at = datetime.now(UTC) - timedelta(days=10)

    before, after = apply_lazy_topic_decay(
        student,
        "topic-1",
        last_attempt_at=last_attempt_at,
        now=datetime.now(UTC),
    )

    assert before == 3.5
    assert after < before
    assert student.topic_skills["topic-1"] == after
