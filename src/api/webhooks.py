import logging
import time
from types import SimpleNamespace

from fastapi import APIRouter, Request, Response, status

from src.app.bootstrap import startup_web_app
from src.cache import redis_client
from src.bot import telegram_app
from src.config import WEBHOOK_SECRET
from src.core.config import get_settings
from src.database import engine
from src.infra.redis.state_store import InteractiveStateStore
from src.infra.redis.idempotency import TelegramUpdateIdempotencyStore
from src.api.telegram_dispatcher import TelegramUpdateDispatcher


logger = logging.getLogger(__name__)
router = APIRouter()


def get_runtime(request: Request):
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is not None:
        return runtime

    return SimpleNamespace(
        settings=get_settings(),
        redis=redis_client,
        db_engine=engine,
        telegram_app=telegram_app,
        state_store=InteractiveStateStore(redis_client),
        dispatcher=None,
    )


async def claim_telegram_update(redis_conn, payload: dict) -> bool:
    update_id = payload.get("update_id")
    if update_id is None:
        return True

    store = TelegramUpdateIdempotencyStore(redis_conn)
    return await store.claim_update(update_id)


def runtime_accepting_webhooks(runtime) -> bool:
    return getattr(runtime, "startup_ready", True)


@router.post("/webhook")
async def telegram_webhook(request: Request):
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and secret_token != WEBHOOK_SECRET:
        logger.warning("Unauthorized webhook request received.")
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    payload = await request.json()
    runtime = get_runtime(request)
    if not runtime_accepting_webhooks(runtime):
        await startup_web_app(runtime)
    if not runtime_accepting_webhooks(runtime):
        logger.warning(
            "Rejecting webhook while runtime is degraded.",
            extra={"startup_error": getattr(runtime, "startup_error", None)},
        )
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    if runtime.dispatcher is None:
        runtime.dispatcher = TelegramUpdateDispatcher(runtime)
        runtime.telegram_app.bot_data.setdefault("background_scheduler", runtime.dispatcher)

    try:
        start = time.perf_counter()
        should_enqueue = await claim_telegram_update(runtime.redis, payload)
        if not should_enqueue:
            logger.info("Duplicate webhook update suppressed in %.2fms.", (time.perf_counter() - start) * 1000)
            return Response(status_code=status.HTTP_200_OK)

        route = await runtime.dispatcher.dispatch(payload)
        logger.info(
            "Webhook accepted route=%s latency_ms=%.2f",
            route,
            (time.perf_counter() - start) * 1000,
        )
        return Response(status_code=status.HTTP_200_OK)
    except Exception:
        logger.exception("Error enqueueing webhook update.")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
