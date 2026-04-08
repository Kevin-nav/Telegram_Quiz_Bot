from __future__ import annotations

from dataclasses import dataclass
import random

import pytest

from src.domains.adaptive.models import AdaptiveQuestionProfile, AttemptHistorySummary
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
        self.ready_calls = []
        self.manifest_calls = []
        self.hydrate_calls = []

    async def list_ready_questions(self, course_id: str):
        self.ready_calls.append(course_id)
        return list(self.rows)

    async def list_ready_question_manifest(self, course_id: str):
        self.manifest_calls.append(course_id)
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
        keys = tuple(question_keys)
        self.hydrate_calls.append(keys)
        allowed = set(keys)
        return [row for row in self.rows if row.question_key in allowed]


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

    async def get_or_create(
        self,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
    ):
        return self.state

    async def update_fields(
        self,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
        **updates,
    ):
        self.update_calls.append((user_id, course_id, bot_id, updates))
        for key, value in updates.items():
            setattr(self.state, key, value)
        return self.state


class FakeAttempt:
    def __init__(self, *, is_correct: bool, created_at=None):
        self.is_correct = is_correct
        self.created_at = created_at


class FakeQuestionAttemptRepository:
    def __init__(self, attempts_by_question_id=None):
        self.attempts_by_question_id = attempts_by_question_id or {}
        self.calls = []

    async def summarize_attempts_for_questions(
        self,
        *,
        user_id: int,
        question_ids,
        bot_id: str | None = None,
    ):
        question_ids = tuple(question_ids)
        self.calls.append((user_id, question_ids, bot_id))
        return {
            question_id: self.attempts_by_question_id.get(question_id)
            for question_id in question_ids
            if question_id in self.attempts_by_question_id
        }


class FakeSrsRecord:
    def __init__(self, question_id: int, box: int = 1):
        self.question_id = question_id
        self.box = box
        self.last_correct_at = None
        self.last_presented_at = None
        self.last_transition_at = None


class FakeStudentQuestionSrsRepository:
    def __init__(self, records=None):
        self.records = records or {}
        self.calls = []

    async def get_many(self, user_id: int, question_ids, *, bot_id: str | None = None):
        question_ids = tuple(question_ids)
        self.calls.append((user_id, question_ids, bot_id))
        return {
            question_id: record
            for question_id, record in self.records.items()
            if question_id in question_ids
        }


class FakeStateStore:
    def __init__(self):
        self.snapshots = {}
        self.selector_snapshots = {}
        self.manifests = {}
        self.invalidations = []

    async def get_adaptive_snapshot(self, user_id: int, course_id: str):
        return self.snapshots.get((user_id, course_id))

    async def set_adaptive_snapshot(self, user_id: int, course_id: str, snapshot: dict):
        self.snapshots[(user_id, course_id)] = snapshot

    async def invalidate_adaptive_snapshot(self, user_id: int, course_id: str):
        self.invalidations.append((user_id, course_id))
        self.snapshots.pop((user_id, course_id), None)

    async def get_course_question_manifest(self, course_id: str):
        return self.manifests.get(course_id)

    async def set_course_question_manifest(self, course_id: str, manifest):
        self.manifests[course_id] = manifest

    async def invalidate_course_question_manifest(self, course_id: str):
        self.manifests.pop(course_id, None)

    async def get_selector_snapshot(self, user_id: int, course_id: str):
        return self.selector_snapshots.get((user_id, course_id))

    async def set_selector_snapshot(self, user_id: int, course_id: str, snapshot: dict):
        self.selector_snapshots[(user_id, course_id)] = snapshot

    async def invalidate_selector_snapshot(self, user_id: int, course_id: str):
        self.selector_snapshots.pop((user_id, course_id), None)


@pytest.mark.asyncio
async def test_adaptive_service_selects_questions_from_batched_inputs():
    state_store = FakeStateStore()
    attempt_repository = FakeQuestionAttemptRepository(
        {
            1: AttemptHistorySummary(total_attempts=1, wrong_attempts=1),
            2: AttemptHistorySummary(total_attempts=1, wrong_attempts=0),
        }
    )
    question_bank_repository = FakeQuestionBankRepository(
        [
            FakeQuestionRow(1, "q1", "topic-a", 2.0),
            FakeQuestionRow(2, "q2", "topic-a", 2.7),
            FakeQuestionRow(3, "q3", "topic-b", 3.0, band=2),
        ]
    )
    service = AdaptiveLearningService(
        question_bank_repository=question_bank_repository,
        question_attempt_repository=attempt_repository,
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
    assert attempt_repository.calls == [(42, (1, 2, 3), None)]
    assert question_bank_repository.manifest_calls == ["calculus"]
    assert len(result.question_rows) == 2
    assert state_store.selector_snapshots[(42, "calculus")]["attempted_question_ids"] == ["q2"]


@pytest.mark.asyncio
async def test_adaptive_service_persists_updated_student_state_after_attempt_update():
    state_repository = FakeStudentCourseStateRepository()
    state_store = FakeStateStore()
    service = AdaptiveLearningService(
        question_bank_repository=FakeQuestionBankRepository([]),
        question_attempt_repository=FakeQuestionAttemptRepository(),
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
    _, _, _, updates = state_repository.update_calls[0]
    assert updates["overall_skill"] > 2.5
    assert updates["total_attempts"] == 1
    assert state_store.invalidations == [(42, "calculus")]


@pytest.mark.asyncio
async def test_adaptive_service_reuses_cached_manifest_and_selector_snapshot():
    state_store = FakeStateStore()
    state_store.manifests["calculus"] = [
        {
            "source_question_id": 1,
            "question_key": "q1",
            "topic_id": "topic-a",
            "scaled_score": 2.0,
            "band": 3,
            "cognitive_level": "Understanding",
            "processing_complexity": 1.0,
            "distractor_complexity": 1.0,
            "note_reference": 1.0,
            "question_type": "MCQ",
            "option_count": 4,
            "has_latex": False,
        },
        {
            "source_question_id": 2,
            "question_key": "q2",
            "topic_id": "topic-b",
            "scaled_score": 2.6,
            "band": 3,
            "cognitive_level": "Understanding",
            "processing_complexity": 1.0,
            "distractor_complexity": 1.0,
            "note_reference": 1.0,
            "question_type": "MCQ",
            "option_count": 4,
            "has_latex": False,
        },
    ]
    state_store.selector_snapshots[(42, "calculus")] = {
        "attempts_by_question": {
            "q1": {
                "total_attempts": 2,
                "wrong_attempts": 1,
                "last_wrong_at": None,
            }
        },
        "recently_correct_at_by_question": {},
        "attempted_question_ids": ["q1"],
        "srs_by_question": {},
    }
    question_bank_repository = FakeQuestionBankRepository(
        [
            FakeQuestionRow(1, "q1", "topic-a", 2.0),
            FakeQuestionRow(2, "q2", "topic-b", 2.6),
        ]
    )
    attempt_repository = FakeQuestionAttemptRepository()
    srs_repository = FakeStudentQuestionSrsRepository()
    service = AdaptiveLearningService(
        question_bank_repository=question_bank_repository,
        question_attempt_repository=attempt_repository,
        student_course_state_repository=FakeStudentCourseStateRepository(),
        student_question_srs_repository=srs_repository,
        state_store=state_store,
    )

    result = await service.select_questions(
        user_id=42,
        course_id="calculus",
        quiz_length=1,
        rng=random.Random(0),
    )

    assert len(result.selected_questions) == 1
    assert question_bank_repository.manifest_calls == []
    assert attempt_repository.calls == []
    assert srs_repository.calls == []
