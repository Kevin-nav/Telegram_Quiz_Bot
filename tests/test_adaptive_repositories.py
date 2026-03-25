from __future__ import annotations

import pytest

from src.infra.db.models.adaptive_review_flag import AdaptiveReviewFlag
from src.infra.db.models.student_course_state import StudentCourseState
from src.infra.db.models.student_question_srs import StudentQuestionSrs
from src.infra.db.repositories.adaptive_review_repository import AdaptiveReviewRepository
from src.infra.db.repositories.student_course_state_repository import StudentCourseStateRepository
from src.infra.db.repositories.student_question_srs_repository import StudentQuestionSrsRepository


class FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class FakeResult:
    def __init__(self, value=None, values=None):
        self._value = value
        self._values = values or []

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return FakeScalarResult(self._values)


class FakeAdaptiveSession:
    def __init__(self):
        self.states_by_key: dict[tuple[int, str], StudentCourseState] = {}
        self.srs_by_key: dict[tuple[int, int], StudentQuestionSrs] = {}
        self.flags_by_key: dict[tuple[int, str], AdaptiveReviewFlag] = {}
        self.state_id_seq = 1
        self.srs_id_seq = 1
        self.flag_id_seq = 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement):
        statement_type = statement.__visit_name__
        params = statement.compile().params
        model = statement.column_descriptions[0]["entity"]

        if statement_type != "select":
            raise AssertionError(f"Unsupported statement: {statement_type}")

        if model is StudentCourseState:
            user_id = self._extract_param(params, "user_id")
            course_id = self._extract_param(params, "course_id")
            return FakeResult(self.states_by_key.get((user_id, course_id)))

        if model is StudentQuestionSrs:
            user_id = self._extract_param(params, "user_id")
            question_id = self._extract_param(params, "question_id")
            if question_id is None or isinstance(question_id, (list, tuple, set)):
                question_ids = self._extract_param(params, "question_id_1")
                values = [
                    record
                    for (record_user_id, record_question_id), record in self.srs_by_key.items()
                    if record_user_id == user_id and record_question_id in question_ids
                ]
                values.sort(key=lambda record: record.question_id)
                return FakeResult(values=values)
            return FakeResult(self.srs_by_key.get((user_id, question_id)))

        if model is AdaptiveReviewFlag:
            question_id = self._extract_param(params, "question_id")
            flag_type = self._extract_param(params, "flag_type")
            status = self._extract_param(params, "status")
            if flag_type is None:
                values = [
                    flag
                    for (record_question_id, _), flag in self.flags_by_key.items()
                    if record_question_id == question_id and flag.status == status
                ]
                values.sort(key=lambda flag: flag.id or 0)
                return FakeResult(values=values)
            return FakeResult(self.flags_by_key.get((question_id, flag_type)))

        raise AssertionError(f"Unsupported model: {model!r}")

    def add(self, record):
        if isinstance(record, StudentCourseState):
            if record.id is None:
                record.id = self.state_id_seq
                self.state_id_seq += 1
            self.states_by_key[(record.user_id, record.course_id)] = record
            return

        if isinstance(record, StudentQuestionSrs):
            if record.id is None:
                record.id = self.srs_id_seq
                self.srs_id_seq += 1
            self.srs_by_key[(record.user_id, record.question_id)] = record
            return

        if isinstance(record, AdaptiveReviewFlag):
            if record.id is None:
                record.id = self.flag_id_seq
                self.flag_id_seq += 1
            self.flags_by_key[(record.question_id, record.flag_type)] = record
            return

        raise AssertionError(f"Unsupported record type: {type(record)!r}")

    async def commit(self):
        return None

    async def refresh(self, record):
        return None

    @staticmethod
    def _extract_param(params: dict, key: str):
        if key in params:
            return params[key]

        for candidate_key, value in params.items():
            if candidate_key.startswith(f"{key}_"):
                return value

        return None


class FakeSessionFactory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


@pytest.mark.asyncio
async def test_student_course_state_repository_get_or_create_and_update_fields():
    session = FakeAdaptiveSession()
    repository = StudentCourseStateRepository(FakeSessionFactory(session))

    created = await repository.get_or_create(42, "calculus")
    assert created.overall_skill == 2.5
    assert created.phase == "cold_start"
    assert created.total_quizzes_completed == 0
    assert created.total_attempts == 0

    updated = await repository.update_fields(
        42,
        "calculus",
        overall_skill=3.1,
        phase="warm",
    )
    incremented = await repository.increment_counters(42, "calculus", quizzes=1, attempts=4)

    assert created.id == updated.id == incremented.id
    assert updated.overall_skill == 3.1
    assert updated.phase == "warm"
    assert incremented.total_quizzes_completed == 1
    assert incremented.total_attempts == 4


@pytest.mark.asyncio
async def test_student_question_srs_repository_batches_and_upserts_records():
    session = FakeAdaptiveSession()
    repository = StudentQuestionSrsRepository(FakeSessionFactory(session))

    first = await repository.upsert(
        user_id=42,
        course_id="calculus",
        question_id=101,
        box=2,
    )
    second = await repository.upsert(
        user_id=42,
        course_id="calculus",
        question_id=101,
        box=4,
    )
    batch = await repository.get_many(42, [101, 102])

    assert first.id == second.id
    assert second.box == 4
    assert batch[101].id == second.id


@pytest.mark.asyncio
async def test_adaptive_review_repository_deduplicates_open_flags_and_resolves_them():
    session = FakeAdaptiveSession()
    repository = AdaptiveReviewRepository(FakeSessionFactory(session))

    created = await repository.create_or_update_open_flag(
        question_id=88,
        flag_type="difficulty_divergence",
        reason="scored difficulty diverges from observed performance",
        suggestion="review rubric",
        metadata={"divergence": 1.5},
    )
    updated = await repository.create_or_update_open_flag(
        question_id=88,
        flag_type="difficulty_divergence",
        reason="divergence still present",
        suggestion="review item",
        metadata={"divergence": 1.7},
    )
    resolved = await repository.resolve_flag(88, "difficulty_divergence")
    open_flags = await repository.list_open_flags(88)

    assert created.id == updated.id == resolved.id
    assert updated.reason == "divergence still present"
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None
    assert open_flags == []
