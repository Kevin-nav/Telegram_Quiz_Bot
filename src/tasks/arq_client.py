import logging

from arq import create_pool
from arq.connections import RedisSettings

from src.config import REDIS_URL


logger = logging.getLogger(__name__)
arq_pool = None


async def init_arq_pool():
    global arq_pool
    if arq_pool is None:
        logger.info("Initializing ARQ connection pool.")
        arq_pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
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


async def enqueue_telegram_update(update_payload: dict):
    """Enqueue a Telegram update payload for background processing."""
    pool = await get_arq_pool()
    await pool.enqueue_job("process_telegram_update", update_payload)
