from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.domains.performance.service import PerformanceService


class FakeQuestionAttemptRepository:
    def __init__(self, attempts):
        self.attempts = attempts
        self.calls = []

    async def list_attempts_for_user(
        self,
        *,
        user_id: int,
        bot_id: str | None = None,
        limit: int | None = None,
    ):
        self.calls.append((user_id, bot_id, limit))
        return list(self.attempts[:limit] if limit is not None else self.attempts)


class FakeStudentCourseStateRepository:
    def __init__(self, states):
        self.states = states
        self.calls = []

    async def list_for_user(self, user_id, *, bot_id=None, course_codes=None):
        self.calls.append((user_id, bot_id, course_codes))
        return list(self.states)


def test_build_summary_aggregates_accuracy_pace_and_course_strength():
    service = PerformanceService(
        question_attempt_repository=FakeQuestionAttemptRepository(
            [
                SimpleNamespace(
                    session_id="s1",
                    course_id="linear-electronics",
                    is_correct=True,
                    time_taken_seconds=10.0,
                    attempt_metadata={"topic_id": "op_amp_basics"},
                ),
                SimpleNamespace(
                    session_id="s1",
                    course_id="linear-electronics",
                    is_correct=False,
                    time_taken_seconds=20.0,
                    attempt_metadata={"topic_id": "op_amp_basics"},
                ),
                SimpleNamespace(
                    session_id="s2",
                    course_id="signals",
                    is_correct=True,
                    time_taken_seconds=12.0,
                    attempt_metadata={"topic_id": "fourier"},
                ),
            ]
        ),
        student_course_state_repository=FakeStudentCourseStateRepository([]),
    )

    summary = service.build_summary_from_attempts(
        [
            SimpleNamespace(
                session_id="s1",
                course_id="linear-electronics",
                is_correct=True,
                time_taken_seconds=10.0,
                attempt_metadata={"topic_id": "op_amp_basics"},
            ),
            SimpleNamespace(
                session_id="s1",
                course_id="linear-electronics",
                is_correct=False,
                time_taken_seconds=20.0,
                attempt_metadata={"topic_id": "op_amp_basics"},
            ),
            SimpleNamespace(
                session_id="s2",
                course_id="signals",
                is_correct=True,
                time_taken_seconds=12.0,
                attempt_metadata={"topic_id": "fourier"},
            ),
        ]
    )

    assert summary["quiz_count"] == 2
    assert summary["attempt_count"] == 3
    assert summary["accuracy_percent"] == 67
    assert summary["average_time_seconds"] == 14.0
    assert summary["strongest_course"] == "Signals"
    assert summary["weakest_course"] == "Linear Electronics"

@pytest.mark.asyncio
async def test_get_summary_returns_empty_shape_for_no_attempts():
    repository = FakeQuestionAttemptRepository([])
    state_repository = FakeStudentCourseStateRepository([])
    service = PerformanceService(
        question_attempt_repository=repository,
        student_course_state_repository=state_repository,
        bot_id="adarkwa",
    )

    summary = await service.get_summary(42)

    assert summary["quiz_count"] == 0
    assert summary["attempt_count"] == 0
    assert summary["accuracy_percent"] == 0
    assert state_repository.calls == [(42, "adarkwa", None)]
    assert repository.calls == [(42, "adarkwa", None)]


@pytest.mark.asyncio
async def test_get_summary_prefers_denormalized_course_metrics():
    repository = FakeQuestionAttemptRepository([])
    state_repository = FakeStudentCourseStateRepository(
        [
            SimpleNamespace(
                course_id="signals",
                total_quizzes_completed=3,
                total_attempts=12,
                total_correct=9,
                avg_time_per_question=11.0,
            ),
            SimpleNamespace(
                course_id="linear-electronics",
                total_quizzes_completed=2,
                total_attempts=8,
                total_correct=4,
                avg_time_per_question=15.0,
            ),
        ]
    )
    service = PerformanceService(
        question_attempt_repository=repository,
        student_course_state_repository=state_repository,
        bot_id="adarkwa",
    )

    summary = await service.get_summary(42)

    assert summary["quiz_count"] == 5
    assert summary["attempt_count"] == 20
    assert summary["accuracy_percent"] == 65
    assert summary["strongest_course"] == "Signals"
    assert summary["weakest_course"] == "Linear Electronics"
    assert repository.calls == []
