import pytest
from tests.fakes import FakeRedis


@pytest.mark.asyncio
async def test_duplicate_update_is_rejected_by_idempotency_store():
    from src.infra.redis.idempotency import (
        AdaptiveAttemptIdempotencyStore,
        TelegramUpdateIdempotencyStore,
    )

    store = TelegramUpdateIdempotencyStore(FakeRedis(), ttl_seconds=300)
    adaptive_store = AdaptiveAttemptIdempotencyStore(FakeRedis(), ttl_seconds=300)

    assert await store.claim_update(1001) is True
    assert await store.claim_update(1001) is False
    assert await adaptive_store.claim_attempt("session-1:0:42") is True
    assert await adaptive_store.claim_attempt("session-1:0:42") is False
