from src.infra.redis.keys import telegram_update_key


class TelegramUpdateIdempotencyStore:
    def __init__(self, redis_client, ttl_seconds: int = 300):
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds

    async def claim_update(self, update_id: int) -> bool:
        result = await self.redis_client.set(
            telegram_update_key(update_id),
            "1",
            ex=self.ttl_seconds,
            nx=True,
        )
        return bool(result)
