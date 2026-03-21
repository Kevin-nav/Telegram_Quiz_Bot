import logging

from src.analytics.internal_analytics import analytics
from src.infra.db.repositories.question_attempt_repository import QuestionAttemptRepository


logger = logging.getLogger(__name__)
question_attempt_repository = QuestionAttemptRepository()


async def record_analytics_event(payload: dict) -> None:
    await analytics.track_event(
        user_id=payload["user_id"],
        event_type=payload["event_type"],
        metadata=payload.get("metadata"),
    )


async def persist_quiz_attempt(payload: dict) -> None:
    logger.info("Persisting quiz attempt payload=%s", payload)
    source_question_id = payload.get("source_question_id")
    if source_question_id is not None:
        await question_attempt_repository.create_attempt(
            {
                "session_id": payload["session_id"],
                "user_id": payload["user_id"],
                "course_id": payload["course_id"],
                "question_id": source_question_id,
                "question_key": payload["question_id"],
                "question_index": payload["question_index"],
                "selected_option_ids": payload.get("selected_option_ids", []),
                "selected_option_text": payload.get("selected_option_text"),
                "correct_option_id": payload.get("correct_option_id"),
                "is_correct": payload["is_correct"],
                "arrangement_hash": payload.get("arrangement_hash"),
                "config_index": payload.get("config_index"),
                "time_taken_seconds": payload.get("time_taken_seconds"),
                "time_allocated_seconds": payload.get("time_allocated_seconds"),
                "attempt_metadata": payload.get("metadata", {}),
            }
        )
    else:
        logger.warning(
            "Skipping canonical question_attempt persistence for payload without source_question_id question_id=%s",
            payload.get("question_id"),
        )
    await analytics.track_event(
        user_id=payload["user_id"],
        event_type="quiz_attempt_persisted",
        metadata=payload,
    )


async def persist_quiz_session_progress(payload: dict) -> None:
    logger.info("Persisting quiz session progress payload=%s", payload)
    await analytics.track_event(
        user_id=payload["user_id"],
        event_type="quiz_session_progress_persisted",
        metadata=payload,
    )


async def generate_quiz_session(payload: dict) -> None:
    logger.info("Generating quiz session payload=%s", payload)


async def rebuild_profile_cache(runtime, payload: dict) -> None:
    profile_service = runtime.telegram_app.bot_data["profile_service"]
    await profile_service.rebuild_cache(payload["user_id"])


async def persist_user_profile(runtime, payload: dict) -> None:
    profile_service = runtime.telegram_app.bot_data["profile_service"]
    await profile_service.persist_profile_record(payload)
