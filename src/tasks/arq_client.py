import logging

from arq import create_pool
from arq.connections import RedisSettings

from src.bot.runtime_config import TANJAH_BOT_ID
from src.config import ARQ_QUEUE_NAME, REDIS_URL


logger = logging.getLogger(__name__)
arq_pool = None


def build_arq_redis_settings() -> RedisSettings:
    settings = RedisSettings.from_dsn(REDIS_URL)
    settings.conn_timeout = 5
    settings.conn_retries = 10
    settings.conn_retry_delay = 1
    settings.retry_on_timeout = True
    return settings


async def init_arq_pool():
    global arq_pool
    if arq_pool is None:
        logger.info("Initializing ARQ connection pool.")
        try:
            arq_pool = await create_pool(
                build_arq_redis_settings(),
                default_queue_name=ARQ_QUEUE_NAME,
            )
        except Exception:
            logger.exception("Unable to initialize the ARQ connection pool.")
            raise
    return arq_pool


async def close_arq_pool():
    global arq_pool
    if arq_pool is not None:
        await arq_pool.aclose()
        arq_pool = None


async def get_arq_pool():
    if arq_pool is None:
        return await init_arq_pool()
    return arq_pool


async def enqueue_telegram_update(
    update_payload: dict,
    *,
    bot_id: str = TANJAH_BOT_ID,
):
    """Enqueue a Telegram update payload for background processing."""
    pool = await get_arq_pool()
    payload = update_payload
    if bot_id != TANJAH_BOT_ID:
        payload = {
            "bot_id": bot_id,
            "payload": update_payload,
        }
    await pool.enqueue_job("process_telegram_update", payload)


async def enqueue_record_analytics_event(payload: dict):
    pool = await get_arq_pool()
    await pool.enqueue_job("record_analytics_event", payload)


async def enqueue_persist_quiz_attempt(payload: dict):
    pool = await get_arq_pool()
    await pool.enqueue_job("persist_quiz_attempt", payload)


async def enqueue_persist_quiz_session_progress(payload: dict):
    pool = await get_arq_pool()
    await pool.enqueue_job("persist_quiz_session_progress", payload)


async def enqueue_persist_question_report(payload: dict):
    pool = await get_arq_pool()
    await pool.enqueue_job("persist_question_report", payload)


async def enqueue_generate_quiz_session(payload: dict):
    pool = await get_arq_pool()
    await pool.enqueue_job("generate_quiz_session", payload)


async def enqueue_rebuild_profile_cache(payload: dict):
    pool = await get_arq_pool()
    await pool.enqueue_job("rebuild_profile_cache", payload)


async def enqueue_persist_user_profile(payload: dict):
    pool = await get_arq_pool()
    await pool.enqueue_job("persist_user_profile", payload)
