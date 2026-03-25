from __future__ import annotations

import random
from types import SimpleNamespace

from src.domains.adaptive.arrangement import (
    arrange_options_latex,
    arrange_options_non_latex,
    choose_latex_config_index,
    detect_position_memorization,
)
from src.domains.adaptive.models import (
    AdaptiveQuestionProfile,
    AdaptiveStudentState,
    AttemptRecord,
)
from src.domains.adaptive.ordering import order_quiz, student_overall_skill
from src.domains.adaptive.srs import (
    SRS_INTERVALS,
    advance_srs_box,
    apply_overdue_demote,
    is_srs_due,
    srs_interval_for_box,
)
from src.domains.adaptive.timing import (
    BASE_TIME_SECONDS,
    calculate_question_time_limit,
    classify_attempt_time,
    time_ratio,
)


def make_question(**overrides):
    payload = {
        "question_id": "q1",
        "topic_id": "topic-1",
        "scaled_score": 3.0,
        "band": 3,
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


def test_calculate_question_time_limit_respects_processing_complexity():
    easy = make_question(scaled_score=1.2, processing_complexity=1.0, note_reference=1.0)
    hard = make_question(scaled_score=4.8, processing_complexity=1.5, note_reference=1.6)

    assert calculate_question_time_limit(easy) == BASE_TIME_SECONDS
    assert calculate_question_time_limit(hard) > calculate_question_time_limit(easy)


def test_classify_attempt_time_uses_correctness_and_speed():
    assert classify_attempt_time(
        is_correct=True, time_taken_seconds=10, time_allocated_seconds=30
    ) == "MASTERED"
    assert classify_attempt_time(
        is_correct=False, time_taken_seconds=26, time_allocated_seconds=30
    ) == "SIGNIFICANT_GAP"


def test_time_ratio_handles_missing_inputs():
    assert time_ratio(None, 30) is None
    assert time_ratio(10, None) is None
    assert time_ratio(15, 30) == 0.5


def test_srs_helpers_cover_box_bounds_and_due_logic():
    assert srs_interval_for_box(-1) == SRS_INTERVALS[0]
    assert srs_interval_for_box(99) == SRS_INTERVALS[-1]
    assert is_srs_due(2, 3) is True
    assert advance_srs_box(5, True) == 6
    assert advance_srs_box(2, False) == 0
    assert apply_overdue_demote(3, 20) == 2


def test_order_quiz_groups_easy_hard_and_keeps_length():
    student = AdaptiveStudentState(overall_skill=2.5)
    questions = [
        make_question(question_id="q1", scaled_score=1.0),
        make_question(question_id="q2", scaled_score=2.0),
        make_question(question_id="q3", scaled_score=3.0),
        make_question(question_id="q4", scaled_score=4.5),
    ]

    ordered = order_quiz(questions, student, rng=random.Random(7))

    assert len(ordered) == 4
    assert student_overall_skill(student) == 2.5
    assert ordered[0].scaled_score <= student.overall_skill


def test_arrange_options_non_latex_shuffles_and_builds_hash():
    question = SimpleNamespace(options=["A", "B", "C", "D"])
    options, arrangement_hash = arrange_options_non_latex(
        question, rng=random.Random(4)
    )

    assert sorted(options) == ["A", "B", "C", "D"]
    assert arrangement_hash
    assert set(arrangement_hash.split("-")) <= {"A", "B", "C", "D"}


def test_arrange_options_latex_prefers_unused_configs():
    question = make_question(has_latex=True)
    config_index = arrange_options_latex(
        question, previous_config_indices=[0, 1, 2], rng=random.Random(1)
    )

    assert config_index == 3
    assert choose_latex_config_index(4, [0, 1, 2], rng=random.Random(1)) == 3


def test_detect_position_memorization_requires_mixed_outcomes():
    attempts = [
        AttemptRecord(is_correct=True, arrangement_hash="A-B-C-D"),
        AttemptRecord(is_correct=False, arrangement_hash="D-C-B-A"),
    ]

    assert detect_position_memorization(attempts) is True
