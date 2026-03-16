import pytest


class FakeRedis:
    def __init__(self):
        self.storage = {}
        self.expiry = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.storage:
            return False
        self.storage[key] = value
        self.expiry[key] = ex
        return True

    async def incr(self, key):
        value = int(self.storage.get(key, 0)) + 1
        self.storage[key] = value
        return value

    async def expire(self, key, seconds):
        self.expiry[key] = seconds
        return True


@pytest.mark.asyncio
async def test_duplicate_update_is_rejected_by_idempotency_store():
    from src.infra.redis.idempotency import TelegramUpdateIdempotencyStore

    store = TelegramUpdateIdempotencyStore(FakeRedis(), ttl_seconds=300)

    assert await store.claim_update(1001) is True
    assert await store.claim_update(1001) is False
