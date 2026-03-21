import pytest
from httpx import AsyncClient
from types import SimpleNamespace

from tests.fakes import FakeRedis


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test the health check endpoint returns 200 OK."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Adarkwa Study Bot is running.",
    }


@pytest.mark.asyncio
async def test_webhook_unauthorized(async_client: AsyncClient):
    """Test webhook with invalid or missing secret token."""
    # Missing secret token
    response = await async_client.post("/webhook", json={"update_id": 123})
    assert response.status_code == 401

    # Invalid secret token
    headers = {"X-Telegram-Bot-Api-Secret-Token": "invalid-secret"}
    response = await async_client.post(
        "/webhook", json={"update_id": 123}, headers=headers
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_authorized(async_client: AsyncClient, monkeypatch):
    dispatched_payloads = []

    class FakeDispatcher:
        async def dispatch(self, payload):
            dispatched_payloads.append(payload)
            return "inline"

    import src.api.webhooks

    monkeypatch.setattr(
        src.api.webhooks,
        "get_runtime",
        lambda request: SimpleNamespace(
            redis=FakeRedis(),
            dispatcher=FakeDispatcher(),
            telegram_app=SimpleNamespace(bot_data={}),
        ),
    )

    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    payload = {
        "update_id": 10000,
        "message": {
            "message_id": 1,
            "date": 1441645532,
            "chat": {"id": 1111111, "type": "private"},
            "text": "/start",
        },
    }

    response = await async_client.post("/webhook", json=payload, headers=headers)
    assert response.status_code == 200
    assert dispatched_payloads == [payload]


@pytest.mark.asyncio
async def test_duplicate_webhook_returns_200_without_enqueue(async_client, monkeypatch):
    dispatch_calls = []

    async def mock_claim(*args, **kwargs):
        return False

    import src.api.webhooks

    monkeypatch.setattr(
        src.api.webhooks,
        "get_runtime",
        lambda request: SimpleNamespace(
            redis=FakeRedis(),
            dispatcher=SimpleNamespace(
                dispatch=lambda payload: dispatch_calls.append(payload)
            ),
            telegram_app=SimpleNamespace(bot_data={}),
        ),
    )
    monkeypatch.setattr(src.api.webhooks, "claim_telegram_update", mock_claim)

    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    response = await async_client.post(
        "/webhook",
        json={"update_id": 10000},
        headers=headers,
    )

    assert response.status_code == 200
    assert dispatch_calls == []


@pytest.mark.asyncio
async def test_webhook_background_update_uses_dispatcher(async_client, monkeypatch):
    routes = []

    class FakeDispatcher:
        async def dispatch(self, payload):
            routes.append(payload)
            return "background"

    import src.api.webhooks

    monkeypatch.setattr(
        src.api.webhooks,
        "get_runtime",
        lambda request: SimpleNamespace(
            redis=FakeRedis(),
            dispatcher=FakeDispatcher(),
            telegram_app=SimpleNamespace(bot_data={}),
        ),
    )

    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    payload = {"update_id": 10001, "message": {"photo": [{"file_id": "abc"}]}}

    response = await async_client.post("/webhook", json=payload, headers=headers)

    assert response.status_code == 200
    assert routes == [payload]


@pytest.mark.asyncio
async def test_ready_endpoint_returns_503_when_dependency_down(async_client, monkeypatch):
    async def mock_check_readiness(*args, **kwargs):
        return {"startup": "ok", "redis": "ok", "database": "error"}

    import src.api.health

    monkeypatch.setattr(src.api.health, "check_readiness", mock_check_readiness)

    response = await async_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_ready_endpoint_reports_degraded_startup(async_client, monkeypatch):
    import src.api.health

    monkeypatch.setattr(
        src.api.health,
        "get_runtime",
        lambda request: SimpleNamespace(
            startup_ready=False,
            startup_error="redis_unavailable:RuntimeError",
            redis=FakeRedis(),
            db_engine=SimpleNamespace(),
        ),
    )

    async def mock_check_readiness(runtime):
        return {"startup": "degraded", "redis": "error", "database": "ok"}

    monkeypatch.setattr(src.api.health, "check_readiness", mock_check_readiness)

    response = await async_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["startup"] == "degraded"
    assert response.json()["detail"] == "redis_unavailable:RuntimeError"


@pytest.mark.asyncio
async def test_webhook_returns_503_when_runtime_is_degraded(async_client, monkeypatch):
    import src.api.webhooks

    monkeypatch.setattr(
        src.api.webhooks,
        "get_runtime",
        lambda request: SimpleNamespace(
            startup_ready=False,
            startup_error="redis_unavailable:RuntimeError",
            dispatcher=None,
            telegram_app=SimpleNamespace(bot_data={}),
            redis=FakeRedis(),
        ),
    )

    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    response = await async_client.post(
        "/webhook",
        json={"update_id": 123},
        headers=headers,
    )

    assert response.status_code == 503
