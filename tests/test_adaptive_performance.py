from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState
from src.domains.adaptive.service import AdaptiveLearningService


@dataclass(slots=True)
class FakeQuestionRow:
    id: int
    question_key: str
    topic_id: str
    scaled_score: float
    band: int = 3
    cognitive_level: str | None = "Understanding"
    processing_complexity: float | None = 1.0
    distractor_complexity: float | None = 1.0
    note_reference: float | None = 1.0
    question_type: str = "MCQ"
    option_count: int = 4
    has_latex: bool = False


class CountingQuestionBankRepository:
    def __init__(self, rows):
        self.rows = list(rows)
        self.manifest_calls = 0
        self.hydrate_calls = 0

    async def list_ready_questions(self, course_id: str):
        self.manifest_calls += 1
        return list(self.rows)

    async def list_ready_question_manifest(self, course_id: str):
        self.manifest_calls += 1
        return [
            {
                "source_question_id": row.id,
                "question_key": row.question_key,
                "topic_id": row.topic_id,
                "scaled_score": row.scaled_score,
                "band": row.band,
                "cognitive_level": row.cognitive_level,
                "processing_complexity": row.processing_complexity,
                "distractor_complexity": row.distractor_complexity,
                "note_reference": row.note_reference,
                "question_type": row.question_type,
                "option_count": row.option_count,
                "has_latex": row.has_latex,
            }
            for row in self.rows
        ]

    async def list_questions_by_keys(self, question_keys):
        self.hydrate_calls += 1
        keys = set(question_keys)
        return [row for row in self.rows if row.question_key in keys]


class CountingStudentCourseStateRepository:
    def __init__(self):
        self.calls = 0

    async def get_or_create(
        self,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
    ):
        self.calls += 1
        return type(
            "State",
            (),
            {
                "overall_skill": 2.5,
                "topic_skills": {},
                "cognitive_profile": {},
                "processing_profile": {},
                "misconception_flags": [],
                "phase": "cold_start",
                "total_quizzes_completed": 0,
                "total_attempts": 0,
                "exam_date": None,
            },
        )()

    async def update_fields(self, *args, **kwargs):
        return None


class CountingStudentQuestionSrsRepository:
    def __init__(self):
        self.calls = 0

    async def get_many(self, user_id: int, question_ids, *, bot_id: str | None = None):
        self.calls += 1
        return {}


class CountingQuestionAttemptRepository:
    def __init__(self):
        self.calls = 0

    async def summarize_attempts_for_questions(
        self,
        *,
        user_id: int,
        question_ids,
        bot_id: str | None = None,
    ):
        self.calls += 1
        return {}


@pytest.mark.asyncio
async def test_selector_uses_batched_repository_calls_only():
    question_bank_repository = CountingQuestionBankRepository(
        [
            FakeQuestionRow(1, "q1", "topic-a", 2.0),
            FakeQuestionRow(2, "q2", "topic-b", 2.5),
            FakeQuestionRow(3, "q3", "topic-c", 3.0),
        ]
    )
    student_course_state_repository = CountingStudentCourseStateRepository()
    student_question_srs_repository = CountingStudentQuestionSrsRepository()
    question_attempt_repository = CountingQuestionAttemptRepository()
    service = AdaptiveLearningService(
        question_bank_repository=question_bank_repository,
        question_attempt_repository=question_attempt_repository,
        student_course_state_repository=student_course_state_repository,
        student_question_srs_repository=student_question_srs_repository,
    )

    result = await service.select_questions(
        user_id=42,
        course_id="calculus",
        quiz_length=2,
    )

    assert len(result.selected_questions) == 2
    assert question_bank_repository.manifest_calls == 1
    assert question_bank_repository.hydrate_calls == 1
    assert question_attempt_repository.calls == 1
    assert student_course_state_repository.calls == 1
    assert student_question_srs_repository.calls == 1
