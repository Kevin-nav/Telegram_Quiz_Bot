import logging
from types import SimpleNamespace

from fastapi import APIRouter, Request, Response, status

from src.cache import redis_client
from src.config import WEBHOOK_SECRET
from src.core.config import get_settings
from src.database import engine
from src.infra.redis.idempotency import TelegramUpdateIdempotencyStore
from src.tasks.arq_client import enqueue_telegram_update


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
    )


async def claim_telegram_update(redis_conn, payload: dict) -> bool:
    update_id = payload.get("update_id")
    if update_id is None:
        return True

    store = TelegramUpdateIdempotencyStore(redis_conn)
    return await store.claim_update(update_id)


@router.post("/webhook")
async def telegram_webhook(request: Request):
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if WEBHOOK_SECRET and secret_token != WEBHOOK_SECRET:
        logger.warning("Unauthorized webhook request received.")
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    payload = await request.json()
    runtime = get_runtime(request)

    try:
        should_enqueue = await claim_telegram_update(runtime.redis, payload)
        if not should_enqueue:
            return Response(status_code=status.HTTP_200_OK)

        await enqueue_telegram_update(payload)
        return Response(status_code=status.HTTP_200_OK)
    except Exception:
        logger.exception("Error enqueueing webhook update.")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
