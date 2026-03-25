from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domains.adaptive.models import AdaptiveQuestionProfile
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


class FakeQuestionBankRepository:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    async def list_ready_questions(self, course_id: str):
        self.calls.append(course_id)
        return list(self.rows)


class FakeStudentCourseStateRecord:
    def __init__(self, **overrides):
        payload = {
            "overall_skill": 2.5,
            "topic_skills": {"topic-a": 2.5},
            "cognitive_profile": {"Understanding": 2.5},
            "processing_profile": {"symbolic": 2.5},
            "misconception_flags": [],
            "phase": "cold_start",
            "total_quizzes_completed": 4,
            "total_attempts": 0,
            "exam_date": None,
        }
        payload.update(overrides)
        self.__dict__.update(payload)


class FakeStudentCourseStateRepository:
    def __init__(self, state=None):
        self.state = state or FakeStudentCourseStateRecord()
        self.update_calls = []

    async def get_or_create(self, user_id: int, course_id: str):
        return self.state

    async def update_fields(self, user_id: int, course_id: str, **updates):
        self.update_calls.append((user_id, course_id, updates))
        for key, value in updates.items():
            setattr(self.state, key, value)
        return self.state


class FakeSrsRecord:
    def __init__(self, question_id: int, box: int = 1):
        self.question_id = question_id
        self.box = box
        self.last_correct_at = None


class FakeStudentQuestionSrsRepository:
    def __init__(self, records=None):
        self.records = records or {}
        self.calls = []

    async def get_many(self, user_id: int, question_ids):
        question_ids = tuple(question_ids)
        self.calls.append((user_id, question_ids))
        return {
            question_id: record
            for question_id, record in self.records.items()
            if question_id in question_ids
        }


class FakeStateStore:
    def __init__(self):
        self.snapshots = {}
        self.invalidations = []

    async def get_adaptive_snapshot(self, user_id: int, course_id: str):
        return self.snapshots.get((user_id, course_id))

    async def set_adaptive_snapshot(self, user_id: int, course_id: str, snapshot: dict):
        self.snapshots[(user_id, course_id)] = snapshot

    async def invalidate_adaptive_snapshot(self, user_id: int, course_id: str):
        self.invalidations.append((user_id, course_id))
        self.snapshots.pop((user_id, course_id), None)


@pytest.mark.asyncio
async def test_adaptive_service_selects_questions_from_batched_inputs():
    state_store = FakeStateStore()
    service = AdaptiveLearningService(
        question_bank_repository=FakeQuestionBankRepository(
            [
                FakeQuestionRow(1, "q1", "topic-a", 2.0),
                FakeQuestionRow(2, "q2", "topic-a", 2.7),
                FakeQuestionRow(3, "q3", "topic-b", 3.0, band=2),
            ]
        ),
        student_course_state_repository=FakeStudentCourseStateRepository(),
        student_question_srs_repository=FakeStudentQuestionSrsRepository(
            {1: FakeSrsRecord(1, box=2)}
        ),
        state_store=state_store,
    )

    result = await service.select_questions(
        user_id=42,
        course_id="calculus",
        quiz_length=2,
        attempts_by_question={"q1": []},
    )

    assert len(result.selected_questions) == 2
    assert all(question.question_id in {"q1", "q2", "q3"} for question in result.selected_questions)
    assert state_store.snapshots[(42, "calculus")]["overall_skill"] == 2.5


@pytest.mark.asyncio
async def test_adaptive_service_persists_updated_student_state_after_attempt_update():
    state_repository = FakeStudentCourseStateRepository()
    state_store = FakeStateStore()
    service = AdaptiveLearningService(
        question_bank_repository=FakeQuestionBankRepository([]),
        student_course_state_repository=state_repository,
        student_question_srs_repository=FakeStudentQuestionSrsRepository(),
        state_store=state_store,
    )

    result = await service.apply_attempt_update(
        user_id=42,
        course_id="calculus",
        question=AdaptiveQuestionProfile(
            question_id="q1",
            topic_id="topic-a",
            scaled_score=3.0,
            cognitive_level="Understanding",
        ),
        is_correct=True,
        time_taken_seconds=10,
        time_allocated_seconds=30,
        processing_target="symbolic",
    )

    assert result.classification == "MASTERED"
    assert state_repository.update_calls
    _, _, updates = state_repository.update_calls[0]
    assert updates["overall_skill"] > 2.5
    assert updates["total_attempts"] == 1
    assert state_store.invalidations == [(42, "calculus")]
