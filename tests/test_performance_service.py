from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.domains.performance.service import PerformanceService


class FakeQuestionAttemptRepository:
    def __init__(self, attempts):
        self.attempts = attempts

    async def list_attempts_for_user(self, *, user_id: int, limit: int | None = None):
        return list(self.attempts[:limit] if limit is not None else self.attempts)


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
        )
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
    service = PerformanceService(
        question_attempt_repository=FakeQuestionAttemptRepository([])
    )

    summary = await service.get_summary(42)

    assert summary["quiz_count"] == 0
    assert summary["attempt_count"] == 0
    assert summary["accuracy_percent"] == 0
