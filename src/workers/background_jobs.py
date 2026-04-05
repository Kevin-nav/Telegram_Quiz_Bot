import logging
from datetime import UTC, datetime

from src.domains.adaptive.models import AdaptiveQuestionProfile
from src.domains.adaptive.review import (
    analyze_distractor_patterns,
    analyze_empirical_difficulty,
    analyze_time_allocation,
)
from src.domains.adaptive.service import AdaptiveLearningService
from src.domains.adaptive.srs import advance_srs_box
from src.analytics.internal_analytics import analytics
from src.cache import redis_client
from src.infra.db.repositories.question_attempt_repository import QuestionAttemptRepository
from src.infra.db.repositories.question_report_repository import QuestionReportRepository
from src.infra.db.repositories.adaptive_review_repository import AdaptiveReviewRepository
from src.infra.db.repositories.student_course_state_repository import (
    StudentCourseStateRepository,
)
from src.infra.db.repositories.student_question_srs_repository import StudentQuestionSrsRepository
from src.infra.redis.admin_cache_store import AdminCacheStore
from src.infra.redis.idempotency import AdaptiveAttemptIdempotencyStore


logger = logging.getLogger(__name__)
question_attempt_repository = QuestionAttemptRepository()
question_report_repository = QuestionReportRepository()
adaptive_learning_service = AdaptiveLearningService()
adaptive_review_repository = AdaptiveReviewRepository()
student_course_state_repository = StudentCourseStateRepository()
student_question_srs_repository = StudentQuestionSrsRepository()
admin_cache_store = AdminCacheStore(redis_client)


async def record_analytics_event(payload: dict) -> None:
    await analytics.track_event(
        user_id=payload["user_id"],
        event_type=payload["event_type"],
        metadata=payload.get("metadata"),
        bot_id=payload.get("bot_id"),
    )


def _attempt_event_id(payload: dict) -> str:
    return f"{payload['session_id']}:{payload['question_index']}:{payload['user_id']}"


def _build_question_profile(payload: dict) -> AdaptiveQuestionProfile | None:
    metadata = payload.get("metadata", {})
    topic_id = metadata.get("topic_id")
    scaled_score = metadata.get("scaled_score")
    if topic_id is None or scaled_score is None:
        return None

    return AdaptiveQuestionProfile(
        question_id=payload["question_id"],
        topic_id=topic_id,
        scaled_score=float(scaled_score),
        band=int(metadata.get("band", 3)),
        cognitive_level=metadata.get("cognitive_level"),
        processing_complexity=metadata.get("processing_complexity"),
        distractor_complexity=metadata.get("distractor_complexity"),
        note_reference=metadata.get("note_reference"),
        question_type=metadata.get("question_type", "MCQ"),
        option_count=int(metadata.get("option_count", 4)),
        has_latex=bool(metadata.get("has_latex", False)),
        arrangement_hash=payload.get("arrangement_hash"),
        config_index=payload.get("config_index"),
    )


async def persist_quiz_attempt(payload: dict, runtime=None) -> None:
    logger.info("Persisting quiz attempt payload=%s", payload)
    lock_token = None
    if runtime is not None:
        idempotency_store = AdaptiveAttemptIdempotencyStore(runtime.redis)
        claimed = await idempotency_store.claim_attempt(_attempt_event_id(payload))
        if not claimed:
            logger.info(
                "Skipping duplicate adaptive attempt update for session_id=%s question_index=%s user_id=%s",
                payload["session_id"],
                payload["question_index"],
                payload["user_id"],
            )
            return

        lock_token = await runtime.state_store.acquire_adaptive_update_lock(
            payload["user_id"],
            payload["course_id"],
        )
        if lock_token is None:
            logger.info(
                "Adaptive update already in progress for user_id=%s course_id=%s; skipping duplicate worker execution.",
                payload["user_id"],
                payload["course_id"],
            )
            return

    source_question_id = payload.get("source_question_id")
    metadata = payload.get("metadata", {})
    try:
        if source_question_id is not None:
            await question_attempt_repository.create_attempt(
                {
                    "session_id": payload["session_id"],
                    "user_id": payload["user_id"],
                    "bot_id": payload.get("bot_id"),
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
                    "attempt_metadata": metadata,
                }
            )
        else:
            logger.warning(
                "Skipping canonical question_attempt persistence for payload without source_question_id question_id=%s",
                payload.get("question_id"),
            )

        topic_id = metadata.get("topic_id")
        if topic_id is not None and metadata.get("scaled_score") is not None:
            scaled_score = metadata.get("scaled_score")
            service = (
                AdaptiveLearningService(state_store=runtime.state_store)
                if runtime is not None
                else adaptive_learning_service
            )
            attempts_for_question = []
            if source_question_id is not None:
                attempts_for_question = (
                    await question_attempt_repository.list_attempts_for_question(
                        user_id=payload["user_id"],
                        question_id=source_question_id,
                        bot_id=payload.get("bot_id"),
                    )
                )
            await service.apply_attempt_update(
                user_id=payload["user_id"],
                bot_id=payload.get("bot_id"),
                course_id=payload["course_id"],
                question=AdaptiveQuestionProfile(
                    question_id=payload["question_id"],
                    topic_id=topic_id,
                    scaled_score=float(scaled_score),
                    band=int(metadata.get("band", 3)),
                    cognitive_level=metadata.get("cognitive_level"),
                    processing_complexity=metadata.get("processing_complexity"),
                    distractor_complexity=metadata.get("distractor_complexity"),
                    note_reference=metadata.get("note_reference"),
                    question_type=metadata.get("question_type", "MCQ"),
                    option_count=int(metadata.get("option_count", 4)),
                    has_latex=bool(metadata.get("has_latex", False)),
                    arrangement_hash=payload.get("arrangement_hash"),
                    config_index=payload.get("config_index"),
                ),
                is_correct=payload["is_correct"],
                time_taken_seconds=payload.get("time_taken_seconds"),
                time_allocated_seconds=payload.get("time_allocated_seconds"),
                selected_distractor=payload.get("selected_option_text"),
                attempts_for_question=attempts_for_question,
            )
            if source_question_id is not None:
                existing_srs = await student_question_srs_repository.get(
                    payload["user_id"],
                    source_question_id,
                    bot_id=payload.get("bot_id"),
                )
                current_box = existing_srs.box if existing_srs is not None else 0
                next_box = advance_srs_box(current_box, payload["is_correct"])
                presented_at_raw = metadata.get("presented_at")
                presented_at = (
                    datetime.fromisoformat(presented_at_raw)
                    if presented_at_raw
                    else datetime.now(UTC)
                )
                now = datetime.now(UTC)
                await student_question_srs_repository.upsert(
                    user_id=payload["user_id"],
                    bot_id=payload.get("bot_id"),
                    course_id=payload["course_id"],
                    question_id=source_question_id,
                    box=next_box,
                    last_presented_at=presented_at,
                    last_correct_at=(
                        now
                        if payload["is_correct"]
                        else existing_srs.last_correct_at if existing_srs is not None else None
                    ),
                    last_transition_at=now,
                )

        await analytics.track_event(
            user_id=payload["user_id"],
            event_type="quiz_attempt_persisted",
            metadata=payload,
            bot_id=payload.get("bot_id"),
        )
        await admin_cache_store.bump_version(
            "analytics-summary",
            bot_id=payload.get("bot_id"),
        )
        await admin_cache_store.bump_version(
            "analytics-student",
            bot_id=payload.get("bot_id"),
        )
    finally:
        if runtime is not None and lock_token is not None:
            await runtime.state_store.release_adaptive_update_lock(
                payload["user_id"],
                payload["course_id"],
                lock_token,
            )


async def review_empirical_difficulty(payload: dict, attempts: list) -> None:
    question = _build_question_profile(payload)
    if question is None:
        return

    finding = analyze_empirical_difficulty(
        question,
        attempts,
        question_id=int(payload["source_question_id"]),
    )
    if finding is None:
        return

    await adaptive_review_repository.create_or_update_open_flag(
        question_id=finding.question_id,
        flag_type=finding.flag_type,
        reason=finding.reason,
        suggestion=finding.suggestion,
        metadata=finding.metadata,
    )


async def review_distractor_patterns(payload: dict, attempts: list) -> None:
    question = _build_question_profile(payload)
    if question is None:
        return

    finding = analyze_distractor_patterns(
        question,
        attempts,
        question_id=int(payload["source_question_id"]),
    )
    if finding is None:
        return

    await adaptive_review_repository.create_or_update_open_flag(
        question_id=finding.question_id,
        flag_type=finding.flag_type,
        reason=finding.reason,
        suggestion=finding.suggestion,
        metadata=finding.metadata,
    )


async def review_time_allocation(payload: dict, attempts: list) -> None:
    question = _build_question_profile(payload)
    if question is None:
        return

    finding = analyze_time_allocation(
        question,
        attempts,
        question_id=int(payload["source_question_id"]),
    )
    if finding is None:
        return

    await adaptive_review_repository.create_or_update_open_flag(
        question_id=finding.question_id,
        flag_type=finding.flag_type,
        reason=finding.reason,
        suggestion=finding.suggestion,
        metadata=finding.metadata,
    )


async def persist_quiz_session_progress(payload: dict, runtime=None) -> None:
    logger.info("Persisting quiz session progress payload=%s", payload)
    if payload.get("status") == "completed":
        await student_course_state_repository.increment_counters(
            payload["user_id"],
            payload["course_id"],
            bot_id=payload.get("bot_id"),
            quizzes=1,
        )
        if runtime is not None:
            await runtime.state_store.invalidate_adaptive_snapshot(
                payload["user_id"],
                payload["course_id"],
            )
    await analytics.track_event(
        user_id=payload["user_id"],
        event_type="quiz_session_progress_persisted",
        metadata=payload,
        bot_id=payload.get("bot_id"),
    )
    await admin_cache_store.bump_version(
        "analytics-summary",
        bot_id=payload.get("bot_id"),
    )
    await admin_cache_store.bump_version(
        "analytics-student",
        bot_id=payload.get("bot_id"),
    )


async def persist_question_report(payload: dict, runtime=None) -> None:
    logger.info("Persisting question report payload=%s", payload)
    await question_report_repository.create_report(payload)
    await analytics.track_event(
        user_id=payload["user_id"],
        event_type="question_report_persisted",
        metadata=payload,
        bot_id=payload.get("bot_id"),
    )
    await admin_cache_store.bump_version(
        "reports-list",
        bot_id=payload.get("bot_id"),
    )
    await admin_cache_store.bump_version(
        "reports-detail",
        bot_id=payload.get("bot_id"),
    )
    await admin_cache_store.bump_version(
        "analytics-student",
        bot_id=payload.get("bot_id"),
    )


async def generate_quiz_session(payload: dict) -> None:
    logger.info("Generating quiz session payload=%s", payload)


async def rebuild_profile_cache(runtime, payload: dict) -> None:
    profile_service = _resolve_profile_service(runtime, payload.get("bot_id"))
    await profile_service.rebuild_cache(payload["user_id"])


async def persist_user_profile(runtime, payload: dict) -> None:
    profile_service = _resolve_profile_service(runtime, payload.get("bot_id"))
    await profile_service.persist_profile_record(payload)


def _resolve_profile_service(runtime, bot_id: str | None):
    telegram_apps = getattr(runtime, "telegram_apps", None)
    if isinstance(telegram_apps, dict) and bot_id in telegram_apps:
        return telegram_apps[bot_id].bot_data["profile_service"]
    return runtime.telegram_app.bot_data["profile_service"]


async def precompute_admin_analytics(payload: dict | None = None) -> None:
    """Precompute analytics summaries for all configured bots.

    Called:
    - On a cron schedule (every 5 minutes) to keep the cache warm
    - After quiz attempts are persisted (via cache version bump)
    """
    from src.bot.runtime_config import ADARKWA_BOT_ID, TANJAH_BOT_ID
    from src.domains.admin.analytics_service import AdminAnalyticsService

    service = AdminAnalyticsService()
    bot_ids = [TANJAH_BOT_ID, ADARKWA_BOT_ID]

    for bot_id in bot_ids:
        try:
            logger.info("Precomputing analytics summary for bot_id=%s", bot_id)
            await service.precompute_summary(active_bot_id=bot_id)
            logger.info("Analytics summary precomputed for bot_id=%s", bot_id)
        except Exception:
            logger.exception(
                "Failed to precompute analytics summary for bot_id=%s", bot_id
            )
