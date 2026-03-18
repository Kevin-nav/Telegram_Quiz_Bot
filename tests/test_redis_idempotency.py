import pytest
from tests.fakes import FakeRedis


@pytest.mark.asyncio
async def test_duplicate_update_is_rejected_by_idempotency_store():
    from src.infra.redis.idempotency import TelegramUpdateIdempotencyStore

    store = TelegramUpdateIdempotencyStore(FakeRedis(), ttl_seconds=300)

    assert await store.claim_update(1001) is True
    assert await store.claim_update(1001) is False
