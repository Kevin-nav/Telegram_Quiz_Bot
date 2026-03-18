import logging

from src.analytics.internal_analytics import analytics


logger = logging.getLogger(__name__)


async def record_analytics_event(payload: dict) -> None:
    await analytics.track_event(
        user_id=payload["user_id"],
        event_type=payload["event_type"],
        metadata=payload.get("metadata"),
    )


async def persist_quiz_attempt(payload: dict) -> None:
    logger.info("Persisting quiz attempt payload=%s", payload)
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
