import pytest

from src.infra.redis.admin_cache_store import AdminCacheStore
from tests.fakes import FakeRedis


@pytest.mark.asyncio
async def test_admin_cache_store_isolates_by_bot_and_scope():
    redis = FakeRedis()
    store = AdminCacheStore(redis)

    await store.set_json(
        "analytics-summary",
        {"value": "tanjah-all"},
        bot_id="tanjah",
        ttl_seconds=60,
    )
    await store.set_json(
        "analytics-summary",
        {"value": "adarkwa-all"},
        bot_id="adarkwa",
        ttl_seconds=60,
    )
    await store.set_json(
        "analytics-summary",
        {"value": "tanjah-limited"},
        bot_id="tanjah",
        course_codes={"calc-1", "calc-2"},
        ttl_seconds=60,
    )

    assert await store.get_json("analytics-summary", bot_id="tanjah") == {
        "value": "tanjah-all"
    }
    assert await store.get_json("analytics-summary", bot_id="adarkwa") == {
        "value": "adarkwa-all"
    }
    assert await store.get_json(
        "analytics-summary",
        bot_id="tanjah",
        course_codes={"calc-1", "calc-2"},
    ) == {"value": "tanjah-limited"}
    assert await store.get_json(
        "analytics-summary",
        bot_id="tanjah",
        course_codes={"calc-1"},
    ) is None


@pytest.mark.asyncio
async def test_admin_cache_store_bump_version_invalidates_cached_payloads():
    redis = FakeRedis()
    store = AdminCacheStore(redis)

    await store.set_json(
        "reports-list",
        {"count": 4},
        bot_id="adarkwa",
        ttl_seconds=60,
        extra_parts=("open", 100, 0),
    )

    assert await store.get_json(
        "reports-list",
        bot_id="adarkwa",
        extra_parts=("open", 100, 0),
    ) == {"count": 4}

    await store.bump_version("reports-list", bot_id="adarkwa")

    assert await store.get_json(
        "reports-list",
        bot_id="adarkwa",
        extra_parts=("open", 100, 0),
    ) is None
