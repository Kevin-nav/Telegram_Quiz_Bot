import logging
from typing import Any

from src.app.bootstrap import (
    create_app_state,
    shutdown_worker_app,
    startup_worker_app,
)
from src.app.observability import initialize_observability
from src.config import ARQ_QUEUE_NAME, SENTRY_DSN
from src.tasks.arq_client import build_arq_redis_settings
from src.workers.telegram_update import (
    process_telegram_update as handle_telegram_update,
)
from src.workers.background_jobs import (
    generate_quiz_session as handle_generate_quiz_session,
    persist_quiz_attempt as handle_persist_quiz_attempt,
    persist_quiz_session_progress as handle_persist_quiz_session_progress,
    persist_user_profile as handle_persist_user_profile,
    review_distractor_patterns as handle_review_distractor_patterns,
    review_empirical_difficulty as handle_review_empirical_difficulty,
    review_time_allocation as handle_review_time_allocation,
    rebuild_profile_cache as handle_rebuild_profile_cache,
    record_analytics_event as handle_record_analytics_event,
)

logger = logging.getLogger("arq.worker")


async def startup(ctx: dict[str, Any]) -> None:
    """Runs when the ARQ worker starts."""
    initialize_observability(SENTRY_DSN)
    runtime = await create_app_state()
    ctx["runtime"] = runtime
    await startup_worker_app(runtime)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Runs when the ARQ worker stops."""
    runtime = ctx.get("runtime")
    if runtime is not None:
        await shutdown_worker_app(runtime)


async def process_telegram_update(ctx: dict[str, Any], payload: dict) -> None:
    """Process a Telegram update in the background worker."""
    runtime = ctx["runtime"]

    try:
        await handle_telegram_update(runtime, payload)
    except Exception:
        logger.exception("Failed to process Telegram update.")
        raise


async def record_analytics_event(ctx: dict[str, Any], payload: dict) -> None:
    await handle_record_analytics_event(payload)


async def persist_quiz_attempt(ctx: dict[str, Any], payload: dict) -> None:
    await handle_persist_quiz_attempt(payload, runtime=ctx["runtime"])


async def persist_quiz_session_progress(ctx: dict[str, Any], payload: dict) -> None:
    await handle_persist_quiz_session_progress(payload)


async def generate_quiz_session(ctx: dict[str, Any], payload: dict) -> None:
    await handle_generate_quiz_session(payload)


async def rebuild_profile_cache(ctx: dict[str, Any], payload: dict) -> None:
    await handle_rebuild_profile_cache(ctx["runtime"], payload)


async def persist_user_profile(ctx: dict[str, Any], payload: dict) -> None:
    await handle_persist_user_profile(ctx["runtime"], payload)


async def review_empirical_difficulty(ctx: dict[str, Any], payload: dict) -> None:
    await handle_review_empirical_difficulty(payload, payload.get("attempts", []))


async def review_distractor_patterns(ctx: dict[str, Any], payload: dict) -> None:
    await handle_review_distractor_patterns(payload, payload.get("attempts", []))


async def review_time_allocation(ctx: dict[str, Any], payload: dict) -> None:
    await handle_review_time_allocation(payload, payload.get("attempts", []))


class WorkerSettings:
    functions = [
        process_telegram_update,
        record_analytics_event,
        persist_quiz_attempt,
        persist_quiz_session_progress,
        generate_quiz_session,
        rebuild_profile_cache,
        persist_user_profile,
        review_empirical_difficulty,
        review_distractor_patterns,
        review_time_allocation,
    ]
    redis_settings = build_arq_redis_settings()
    queue_name = ARQ_QUEUE_NAME
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = 60
    max_tries = 3
    poll_delay = 0.05
