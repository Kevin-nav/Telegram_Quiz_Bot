from src.infra.redis.keys import rate_limit_key


class RateLimiter:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def allow(self, user_id: int, action: str, limit: int, window_seconds: int) -> bool:
        key = rate_limit_key(user_id, action)
        current = await self.redis_client.incr(key)
        if current == 1:
            await self.redis_client.expire(key, window_seconds)
        return current <= limit
