from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.domains.adaptive.review import (
    analyze_distractor_patterns,
    analyze_empirical_difficulty,
    analyze_time_allocation,
)
from src.domains.adaptive.models import AdaptiveQuestionProfile
from src.workers.background_jobs import (
    persist_question_report,
    persist_quiz_attempt,
    persist_quiz_session_progress,
    persist_user_profile,
    rebuild_profile_cache,
    review_distractor_patterns,
    review_empirical_difficulty,
    review_time_allocation,
)
from tests.fakes import FakeRedis


def make_question(**overrides):
    payload = {
        "question_id": 17,
        "topic_id": "op_amp_basics",
        "scaled_score": 2.0,
        "band": 2,
        "cognitive_level": "Understanding",
        "processing_complexity": 1.0,
        "distractor_complexity": 1.2,
        "note_reference": 1.0,
        "question_type": "MCQ",
        "option_count": 4,
        "has_latex": False,
    }
    payload.update(overrides)
    return AdaptiveQuestionProfile(**payload)


class FakeAttempt:
    def __init__(self, *, is_correct, selected_option_id=None, time_taken_seconds=None):
        self.is_correct = is_correct
        self.selected_option_id = selected_option_id
        self.time_taken_seconds = time_taken_seconds


@pytest.mark.asyncio
async def test_persisted_attempt_includes_arrangement_hash_or_config_index():
    payload = {
        "session_id": "session-1",
        "user_id": 42,
        "bot_id": "adarkwa",
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
            "scaled_score": 2.0,
            "band": 2,
            "cognitive_level": "Understanding",
            "processing_complexity": 1.0,
            "distractor_complexity": 1.2,
            "note_reference": 1.0,
            "question_type": "MCQ",
            "option_count": 4,
            "has_latex": False,
        },
    }

    with (
        patch(
            "src.workers.background_jobs.question_attempt_repository.create_attempt",
            new=AsyncMock(),
        ) as create_attempt,
        patch(
            "src.workers.background_jobs.student_question_srs_repository.get",
            new=AsyncMock(return_value=None),
        ) as get_srs,
        patch(
            "src.workers.background_jobs.question_attempt_repository.list_attempts_for_question",
            new=AsyncMock(return_value=[]),
        ) as list_attempts,
        patch(
            "src.workers.background_jobs.student_question_srs_repository.upsert",
            new=AsyncMock(),
        ) as upsert_srs,
        patch(
            "src.workers.background_jobs.adaptive_learning_service.apply_attempt_update",
            new=AsyncMock(),
        ) as apply_attempt_update,
        patch(
            "src.workers.background_jobs.analytics.track_event",
            new=AsyncMock(),
        ) as track_event,
        patch(
            "src.workers.background_jobs.student_course_state_repository.record_attempt_metrics",
            new=AsyncMock(),
        ),
        patch(
            "src.workers.background_jobs.user_repository.touch_activity",
            new=AsyncMock(),
        ),
    ):
        await persist_quiz_attempt(payload)

    persisted_payload = create_attempt.await_args.args[0]
    assert persisted_payload["bot_id"] == "adarkwa"
    assert persisted_payload["question_id"] == 17
    assert persisted_payload["question_key"] == "linear-electronics-q1"
    assert persisted_payload["arrangement_hash"] == "C-A-D-B"
    assert persisted_payload["config_index"] is None
    assert persisted_payload["attempt_metadata"]["topic_id"] == "op_amp_basics"
    apply_payload = apply_attempt_update.await_args.kwargs
    assert apply_payload["bot_id"] == "adarkwa"
    assert apply_payload["question"].question_id == "linear-electronics-q1"
    assert apply_payload["question"].scaled_score == 2.0
    assert apply_payload["selected_distractor"] == "C"
    list_attempts.assert_awaited_once_with(user_id=42, question_id=17, bot_id="adarkwa")
    get_srs.assert_awaited_once_with(42, 17, bot_id="adarkwa")
    upsert_payload = upsert_srs.await_args.kwargs
    assert upsert_payload["bot_id"] == "adarkwa"
    assert upsert_payload["question_id"] == 17
    assert upsert_payload["box"] == 0
    assert track_event.await_args.kwargs["bot_id"] == "adarkwa"


def test_review_helpers_flag_large_divergence_and_common_distractors():
    question = make_question()
    difficulty_attempts = [FakeAttempt(is_correct=False) for _ in range(8)] + [
        FakeAttempt(is_correct=True) for _ in range(2)
    ]
    distractor_attempts = [
        FakeAttempt(is_correct=False, selected_option_id=1) for _ in range(10)
    ] + [
        FakeAttempt(is_correct=False, selected_option_id=2) for _ in range(5)
    ]
    time_attempts = [
        FakeAttempt(is_correct=True, time_taken_seconds=10 + index)
        for index in range(15)
    ]

    difficulty = analyze_empirical_difficulty(question, difficulty_attempts, question_id=17)
    distractor = analyze_distractor_patterns(question, distractor_attempts, question_id=17)
    timing = analyze_time_allocation(question, time_attempts, question_id=17)

    assert difficulty is not None
    assert difficulty.flag_type == "difficulty_divergence"
    assert distractor is not None
    assert distractor.flag_type == "distractor_bias"
    assert timing is not None
    assert timing.flag_type == "time_limit_review"


@pytest.mark.asyncio
async def test_review_worker_functions_persist_open_flags():
    payload = {
        "session_id": "session-1",
        "user_id": 42,
        "bot_id": "adarkwa",
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
            "scaled_score": 2.0,
            "band": 2,
            "cognitive_level": "Understanding",
            "processing_complexity": 1.0,
            "distractor_complexity": 1.2,
            "note_reference": 1.0,
            "question_type": "MCQ",
            "option_count": 4,
            "has_latex": False,
        },
    }
    attempts = [
        FakeAttempt(is_correct=False, selected_option_id=2, time_taken_seconds=19.0)
        for _ in range(16)
    ]

    with patch(
        "src.workers.background_jobs.adaptive_review_repository.create_or_update_open_flag",
        new=AsyncMock(),
    ) as create_flag:
        await review_empirical_difficulty(payload, attempts)
        await review_distractor_patterns(payload, attempts)
        await review_time_allocation(payload, attempts)

    assert create_flag.await_count == 3
    assert {call.kwargs["flag_type"] for call in create_flag.await_args_list} == {
        "difficulty_divergence",
        "distractor_bias",
        "time_limit_review",
    }


@pytest.mark.asyncio
async def test_completed_quiz_progress_increments_quiz_counter():
    payload = {
        "session_id": "session-1",
        "user_id": 42,
        "bot_id": "adarkwa",
        "course_id": "linear-electronics",
        "status": "completed",
        "score": 8,
        "total_questions": 10,
    }

    with (
        patch(
            "src.workers.background_jobs.student_course_state_repository.increment_counters",
            new=AsyncMock(),
        ) as increment_counters,
        patch(
            "src.workers.background_jobs.question_attempt_repository.list_attempts_for_session",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.workers.background_jobs.student_session_summary_repository.upsert_summary",
            new=AsyncMock(),
        ),
        patch(
            "src.workers.background_jobs.user_repository.touch_activity",
            new=AsyncMock(),
        ),
        patch(
            "src.workers.background_jobs.analytics.track_event",
            new=AsyncMock(),
        ) as track_event,
    ):
        await persist_quiz_session_progress(payload)

    increment_counters.assert_awaited_once_with(
        42,
        "linear-electronics",
        quizzes=1,
        bot_id="adarkwa",
    )
    assert track_event.await_args.kwargs["bot_id"] == "adarkwa"


@pytest.mark.asyncio
async def test_completed_quiz_progress_persists_session_summary():
    payload = {
        "session_id": "session-1",
        "user_id": 42,
        "bot_id": "adarkwa",
        "course_id": "linear-electronics",
        "status": "completed",
        "total_questions": 3,
        "completed_at": "2026-04-08T00:00:00+00:00",
    }
    attempts = [
        SimpleNamespace(is_correct=True, time_taken_seconds=10.0),
        SimpleNamespace(is_correct=False, time_taken_seconds=20.0),
        SimpleNamespace(is_correct=True, time_taken_seconds=14.0),
    ]

    with (
        patch(
            "src.workers.background_jobs.student_course_state_repository.increment_counters",
            new=AsyncMock(),
        ),
        patch(
            "src.workers.background_jobs.question_attempt_repository.list_attempts_for_session",
            new=AsyncMock(return_value=attempts),
        ),
        patch(
            "src.workers.background_jobs.student_session_summary_repository.upsert_summary",
            new=AsyncMock(),
        ) as upsert_summary,
        patch(
            "src.workers.background_jobs.user_repository.touch_activity",
            new=AsyncMock(),
        ),
        patch(
            "src.workers.background_jobs.analytics.track_event",
            new=AsyncMock(),
        ),
    ):
        await persist_quiz_session_progress(payload)

    summary_kwargs = upsert_summary.await_args.kwargs
    assert summary_kwargs["session_id"] == "session-1"
    assert summary_kwargs["correct_count"] == 2
    assert summary_kwargs["avg_time_seconds"] == 14.7


@pytest.mark.asyncio
async def test_persist_quiz_attempt_updates_selector_snapshot_when_runtime_exists():
    payload = {
        "session_id": "session-1",
        "user_id": 42,
        "bot_id": "adarkwa",
        "course_id": "linear-electronics",
        "question_id": "linear-electronics-q1",
        "source_question_id": 17,
        "question_index": 0,
        "selected_option_ids": [1],
        "selected_option_text": "A",
        "correct_option_id": 1,
        "is_correct": True,
        "time_taken_seconds": 12.0,
        "time_allocated_seconds": 45,
        "metadata": {
            "topic_id": "op_amp_basics",
            "scaled_score": 2.0,
            "band": 2,
            "cognitive_level": "Understanding",
            "processing_complexity": 1.0,
            "distractor_complexity": 1.2,
            "note_reference": 1.0,
            "question_type": "MCQ",
            "option_count": 4,
            "has_latex": False,
        },
    }
    runtime = SimpleNamespace(
        redis=FakeRedis(),
        state_store=SimpleNamespace(
            acquire_adaptive_update_lock=AsyncMock(return_value="lock-token"),
            release_adaptive_update_lock=AsyncMock(),
            record_selector_attempt=AsyncMock(),
        ),
    )
    now = datetime(2026, 4, 8, tzinfo=timezone.utc)
    persisted_attempt = SimpleNamespace(created_at=now)
    srs_record = SimpleNamespace(
        box=1,
        last_presented_at=now,
        last_correct_at=now,
        last_transition_at=now,
    )

    with (
        patch(
            "src.workers.background_jobs.question_attempt_repository.create_attempt",
            new=AsyncMock(return_value=persisted_attempt),
        ),
        patch(
            "src.workers.background_jobs.question_attempt_repository.list_attempts_for_question",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.workers.background_jobs.student_question_srs_repository.get",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "src.workers.background_jobs.student_question_srs_repository.upsert",
            new=AsyncMock(return_value=srs_record),
        ),
        patch(
            "src.workers.background_jobs.analytics.track_event",
            new=AsyncMock(),
        ),
        patch(
            "src.domains.adaptive.service.AdaptiveLearningService.apply_attempt_update",
            new=AsyncMock(),
        ),
        patch(
            "src.workers.background_jobs.student_course_state_repository.record_attempt_metrics",
            new=AsyncMock(),
        ),
        patch(
            "src.workers.background_jobs.user_repository.touch_activity",
            new=AsyncMock(),
        ),
    ):
        await persist_quiz_attempt(payload, runtime=runtime)

    runtime.state_store.record_selector_attempt.assert_awaited_once()
    record_kwargs = runtime.state_store.record_selector_attempt.await_args.kwargs
    assert record_kwargs["question_key"] == "linear-electronics-q1"
    assert record_kwargs["srs_state"]["box"] == 1


@pytest.mark.asyncio
async def test_persist_question_report_creates_row_and_tracks_event():
    payload = {
        "user_id": 42,
        "bot_id": "adarkwa",
        "session_id": "session-1",
        "course_id": "linear-electronics",
        "question_id": 17,
        "question_key": "linear-electronics-q1",
        "question_index": 0,
        "report_scope": "answer",
        "report_reason": "correct_answer_shown_is_wrong",
        "report_note": "The keyed answer should be option B.",
        "report_metadata": {"correct_option_text": "B"},
    }

    with (
        patch(
            "src.workers.background_jobs.question_report_repository.create_report",
            new=AsyncMock(),
        ) as create_report,
        patch(
            "src.workers.background_jobs.analytics.track_event",
            new=AsyncMock(),
        ) as track_event,
    ):
        await persist_question_report(payload)

    create_report.assert_awaited_once_with(payload)
    assert track_event.await_args.kwargs["bot_id"] == "adarkwa"


@pytest.mark.asyncio
async def test_profile_background_jobs_resolve_profile_service_by_bot_id():
    tanjah_profile_service = SimpleNamespace(
        rebuild_cache=AsyncMock(),
        persist_profile_record=AsyncMock(),
    )
    adarkwa_profile_service = SimpleNamespace(
        rebuild_cache=AsyncMock(),
        persist_profile_record=AsyncMock(),
    )
    runtime = SimpleNamespace(
        telegram_app=SimpleNamespace(bot_data={"profile_service": tanjah_profile_service}),
        telegram_apps={
            "tanjah": SimpleNamespace(bot_data={"profile_service": tanjah_profile_service}),
            "adarkwa": SimpleNamespace(bot_data={"profile_service": adarkwa_profile_service}),
        },
    )

    await rebuild_profile_cache(runtime, {"user_id": 42, "bot_id": "adarkwa"})
    await persist_user_profile(runtime, {"user_id": 42, "bot_id": "adarkwa"})

    adarkwa_profile_service.rebuild_cache.assert_awaited_once_with(42)
    adarkwa_profile_service.persist_profile_record.assert_awaited_once_with(
        {"user_id": 42, "bot_id": "adarkwa"}
    )
    tanjah_profile_service.rebuild_cache.assert_not_called()
    tanjah_profile_service.persist_profile_record.assert_not_called()
