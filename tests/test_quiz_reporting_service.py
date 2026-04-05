from __future__ import annotations

import pytest

from src.domains.quiz.models import QuizQuestion, QuizSessionState
from src.domains.quiz_reporting.service import QuizReportingService


def _build_session() -> QuizSessionState:
    return QuizSessionState(
        session_id="session-1",
        user_id=42,
        chat_id=99,
        course_id="linear-electronics",
        course_name="Linear Electronics",
        questions=[
            QuizQuestion(
                question_id="q1",
                source_question_id=17,
                prompt="What is shown?",
                options=["A", "B", "C", "D"],
                correct_option_id=1,
                explanation="Option B is correct.",
                has_latex=False,
            ),
            QuizQuestion(
                question_id="q2",
                source_question_id=18,
                prompt="Second question",
                options=["A", "B"],
                correct_option_id=0,
                explanation="Option A is correct.",
                has_latex=True,
            ),
        ],
        current_index=1,
        last_answered_question_id="q1",
        last_answered_question_index=0,
    )


def test_validate_reason_accepts_reason_for_matching_scope():
    service = QuizReportingService()

    service.validate_reason("question", "question_unclear")
    service.validate_reason("answer", "correct_answer_shown_is_wrong")


def test_validate_reason_rejects_reason_for_wrong_scope():
    service = QuizReportingService()

    with pytest.raises(ValueError):
        service.validate_reason("question", "correct_answer_shown_is_wrong")


def test_build_question_report_payload_uses_current_question_context():
    service = QuizReportingService()
    payload = service.build_report_payload(
        session=_build_session(),
        bot_id="adarkwa",
        report_scope="question",
        report_reason="image_or_latex_issue",
        report_note="The rendering is cropped.",
    )

    assert payload["bot_id"] == "adarkwa"
    assert payload["question_id"] == 18
    assert payload["question_key"] == "q2"
    assert payload["report_scope"] == "question"
    assert payload["report_reason"] == "image_or_latex_issue"
    assert payload["report_note"] == "The rendering is cropped."
    assert payload["report_metadata"]["has_latex"] is True


def test_build_answer_report_payload_uses_last_answered_context():
    service = QuizReportingService()
    payload = service.build_report_payload(
        session=_build_session(),
        bot_id="tanjah",
        report_scope="answer",
        report_reason="explanation_is_wrong",
        report_note=None,
    )

    assert payload["bot_id"] == "tanjah"
    assert payload["question_id"] == 17
    assert payload["question_key"] == "q1"
    assert payload["question_index"] == 0
    assert payload["report_scope"] == "answer"
    assert payload["report_metadata"]["correct_option_text"] == "B"
    assert payload["report_metadata"]["has_explanation"] is True
