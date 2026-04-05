from src.bot.runtime_config import TANJAH_BOT_ID
from src.infra.redis.keys import adaptive_attempt_key, telegram_update_key


class TelegramUpdateIdempotencyStore:
    def __init__(
        self,
        redis_client,
        ttl_seconds: int = 300,
        bot_id: str = TANJAH_BOT_ID,
    ):
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds
        self.bot_id = bot_id

    async def claim_update(self, update_id: int) -> bool:
        result = await self.redis_client.set(
            telegram_update_key(update_id, self.bot_id),
            "1",
            ex=self.ttl_seconds,
            nx=True,
        )
        return bool(result)


class AdaptiveAttemptIdempotencyStore:
    def __init__(self, redis_client, ttl_seconds: int = 24 * 60 * 60):
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds

    async def claim_attempt(self, attempt_id: str) -> bool:
        result = await self.redis_client.set(
            adaptive_attempt_key(attempt_id),
            "1",
            ex=self.ttl_seconds,
            nx=True,
        )
        return bool(result)
