from unittest.mock import AsyncMock, patch

import pytest

from src.workers.background_jobs import persist_quiz_attempt


@pytest.mark.asyncio
async def test_persisted_attempt_includes_arrangement_hash_or_config_index():
    payload = {
        "session_id": "session-1",
        "user_id": 42,
        "course_id": "linear-electronics",
        "question_id": "linear-electronics-q1",
        "source_question_id": 17,
        "question_index": 0,
        "selected_option_ids": [2],
        "selected_option_text": "C",
        "correct_option_id": 1,
        "is_correct": False,
        "arrangement_hash": "C-A-D-B",
        "config_index": None,
        "time_taken_seconds": 19.0,
        "time_allocated_seconds": 45,
        "metadata": {
            "topic_id": "op_amp_basics",
            "has_latex": False,
        },
    }

    with (
        patch(
            "src.workers.background_jobs.question_attempt_repository.create_attempt",
            new=AsyncMock(),
        ) as create_attempt,
        patch(
            "src.workers.background_jobs.analytics.track_event",
            new=AsyncMock(),
        ) as track_event,
    ):
        await persist_quiz_attempt(payload)

    persisted_payload = create_attempt.await_args.args[0]
    assert persisted_payload["question_id"] == 17
    assert persisted_payload["question_key"] == "linear-electronics-q1"
    assert persisted_payload["arrangement_hash"] == "C-A-D-B"
    assert persisted_payload["config_index"] is None
    assert persisted_payload["attempt_metadata"]["topic_id"] == "op_amp_basics"
    track_event.assert_awaited_once()
