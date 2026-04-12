import logging
import time
from types import SimpleNamespace

from fastapi import APIRouter, Request, Response, status

from src.app.bootstrap import startup_web_app
from src.bot import telegram_app
from src.bot.runtime_config import (
    ADARKWA_BOT_ID,
    DEFAULT_BOT_THEMES,
    TANJAH_BOT_ID,
    BotRuntimeConfig,
)
from src.cache import redis_client
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


async def claim_telegram_update(
    redis_conn,
    payload: dict,
    *,
    bot_id: str = TANJAH_BOT_ID,
) -> bool:
    update_id = payload.get("update_id")
    if update_id is None:
        return True

    store = TelegramUpdateIdempotencyStore(redis_conn, bot_id=bot_id)
    return await store.claim_update(update_id)


def runtime_accepting_webhooks(runtime) -> bool:
    return getattr(runtime, "startup_ready", True)


def runtime_queue_only(runtime) -> bool:
    settings = getattr(runtime, "settings", None)
    return getattr(settings, "app_mode", "normal") == "queue_only"


@router.post("/webhook")
@router.post("/webhook/{bot_id}")
async def telegram_webhook(request: Request, bot_id: str = TANJAH_BOT_ID):
    runtime = get_runtime(request)
    bot_config = resolve_webhook_bot_config(runtime, bot_id)
    if bot_config is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if bot_config.webhook_secret and secret_token != bot_config.webhook_secret:
        logger.warning("Unauthorized webhook request received.")
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    payload = await request.json()
    if not runtime_accepting_webhooks(runtime):
        await startup_web_app(runtime)
    if not runtime_accepting_webhooks(runtime):
        logger.warning(
            "Rejecting webhook while runtime is degraded.",
            extra={"startup_error": getattr(runtime, "startup_error", None)},
        )
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    if runtime.dispatcher is None:
        runtime.dispatcher = TelegramUpdateDispatcher(
            runtime,
            force_background=runtime_queue_only(runtime),
        )
        runtime.telegram_app.bot_data.setdefault("background_scheduler", runtime.dispatcher)

    try:
        start = time.perf_counter()
        should_enqueue = await claim_telegram_update(
            runtime.redis,
            payload,
            bot_id=bot_config.bot_id,
        )
        if not should_enqueue:
            logger.info("Duplicate webhook update suppressed in %.2fms.", (time.perf_counter() - start) * 1000)
            return Response(status_code=status.HTTP_200_OK)

        route = await dispatch_telegram_update(
            runtime.dispatcher,
            payload,
            bot_id=bot_config.bot_id,
        )
        logger.info(
            "Webhook accepted route=%s latency_ms=%.2f",
            route,
            (time.perf_counter() - start) * 1000,
        )
        return Response(status_code=status.HTTP_200_OK)
    except Exception:
        logger.exception("Error enqueueing webhook update.")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def resolve_webhook_bot_config(runtime, bot_id: str) -> BotRuntimeConfig | None:
    bot_configs = getattr(getattr(runtime, "settings", None), "bot_configs", None)
    if isinstance(bot_configs, dict):
        return bot_configs.get(bot_id)

    if bot_id not in {TANJAH_BOT_ID, ADARKWA_BOT_ID}:
        return None
    if bot_id == ADARKWA_BOT_ID:
        return None

    return BotRuntimeConfig(
        bot_id=TANJAH_BOT_ID,
        telegram_bot_token=None,
        webhook_secret=WEBHOOK_SECRET,
        webhook_path="/webhook",
        allowed_course_codes=(),
        theme=DEFAULT_BOT_THEMES[TANJAH_BOT_ID],
    )


async def dispatch_telegram_update(dispatcher, payload: dict, *, bot_id: str) -> str:
    try:
        return await dispatcher.dispatch(payload, bot_id=bot_id)
    except TypeError:
        return await dispatcher.dispatch(payload)
