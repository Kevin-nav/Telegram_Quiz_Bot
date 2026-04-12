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
async def test_webhook_routes_adarkwa_updates_with_adarkwa_secret(
    async_client: AsyncClient,
    monkeypatch,
):
    dispatched_calls = []

    class FakeDispatcher:
        async def dispatch(self, payload, *, bot_id="tanjah"):
            dispatched_calls.append((bot_id, payload))
            return "inline"

    import src.api.webhooks
    from src.bot.runtime_config import DEFAULT_BOT_THEMES, BotRuntimeConfig

    monkeypatch.setattr(
        src.api.webhooks,
        "get_runtime",
        lambda request: SimpleNamespace(
            settings=SimpleNamespace(
                bot_configs={
                    "tanjah": BotRuntimeConfig(
                        bot_id="tanjah",
                        telegram_bot_token="tanjah-token",
                        webhook_secret="test-secret",
                        webhook_path="/webhook/tanjah",
                        allowed_course_codes=(),
                        theme=DEFAULT_BOT_THEMES["tanjah"],
                    ),
                    "adarkwa": BotRuntimeConfig(
                        bot_id="adarkwa",
                        telegram_bot_token="adarkwa-token",
                        webhook_secret="adarkwa-secret",
                        webhook_path="/webhook/adarkwa",
                        allowed_course_codes=("linear-algebra",),
                        theme=DEFAULT_BOT_THEMES["adarkwa"],
                    ),
                }
            ),
            redis=FakeRedis(),
            dispatcher=FakeDispatcher(),
            telegram_app=SimpleNamespace(bot_data={}),
        ),
    )

    payload = {"update_id": 10002, "message": {"text": "/start"}}

    response = await async_client.post(
        "/webhook/adarkwa",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "adarkwa-secret"},
    )

    assert response.status_code == 200
    assert dispatched_calls == [("adarkwa", payload)]

    response = await async_client.post(
        "/webhook/adarkwa",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
    )

    assert response.status_code == 401


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
async def test_webhook_uses_queue_only_dispatcher_when_app_mode_requires_it(
    async_client,
    monkeypatch,
):
    dispatch_calls = []

    class FakeDispatcher:
        def __init__(self, runtime, *, force_background=False, inline_capacity=100):
            dispatch_calls.append(force_background)
            self.runtime = runtime

        async def dispatch(self, payload, *, bot_id="tanjah"):
            return "background"

    import src.api.webhooks

    monkeypatch.setattr(
        src.api.webhooks,
        "TelegramUpdateDispatcher",
        FakeDispatcher,
    )
    monkeypatch.setattr(
        src.api.webhooks,
        "get_runtime",
        lambda request: SimpleNamespace(
            settings=SimpleNamespace(app_mode="queue_only"),
            redis=FakeRedis(),
            dispatcher=None,
            telegram_app=SimpleNamespace(bot_data={}),
        ),
    )

    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    payload = {"update_id": 10003, "message": {"text": "/start"}}

    response = await async_client.post("/webhook", json=payload, headers=headers)

    assert response.status_code == 200
    assert dispatch_calls == [True]


@pytest.mark.asyncio
async def test_ready_endpoint_returns_503_when_dependency_down(async_client, monkeypatch):
    async def mock_check_readiness(*args, **kwargs):
        return {"startup": "ok", "redis": "ok", "database": "error"}

    import src.api.health

    monkeypatch.setattr(src.api.health, "check_readiness", mock_check_readiness)

    response = await async_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["app_mode"] == "normal"


@pytest.mark.asyncio
async def test_ready_endpoint_reports_degraded_startup(async_client, monkeypatch):
    import src.api.health

    runtime = SimpleNamespace(
        startup_ready=False,
        startup_error="redis_unavailable:RuntimeError",
        settings=SimpleNamespace(app_mode="queue_only"),
        redis=FakeRedis(),
        db_engine=SimpleNamespace(),
    )

    monkeypatch.setattr(
        src.api.health,
        "get_runtime",
        lambda request: runtime,
    )

    async def mock_check_readiness(runtime):
        if runtime.startup_ready:
            return {"startup": "ok", "redis": "ok", "database": "ok"}
        return {"startup": "degraded", "redis": "error", "database": "ok"}

    monkeypatch.setattr(src.api.health, "check_readiness", mock_check_readiness)
    monkeypatch.setattr(
        src.api.health,
        "startup_web_app",
        lambda runtime: _mark_runtime_ready(runtime),
    )

    response = await async_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["startup"] == "ok"
    assert response.json()["app_mode"] == "queue_only"
    assert response.json()["detail"] is None


@pytest.mark.asyncio
async def test_webhook_returns_503_when_runtime_is_degraded(async_client, monkeypatch):
    import src.api.webhooks

    async def fake_startup_web_app(runtime):
        return None

    monkeypatch.setattr(src.api.webhooks, "startup_web_app", fake_startup_web_app)
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


async def _mark_runtime_ready(runtime):
    runtime.startup_ready = True
    runtime.startup_error = None


@pytest.mark.asyncio
async def test_webhook_recovers_runtime_before_accepting_request(async_client, monkeypatch):
    import src.api.webhooks

    dispatched_payloads = []

    class FakeDispatcher:
        async def dispatch(self, payload):
            dispatched_payloads.append(payload)
            return "inline"

    runtime = SimpleNamespace(
        startup_ready=False,
        startup_error="redis_unavailable:RuntimeError",
        dispatcher=None,
        telegram_app=SimpleNamespace(bot_data={}),
        redis=FakeRedis(),
    )

    monkeypatch.setattr(src.api.webhooks, "get_runtime", lambda request: runtime)

    async def fake_startup_web_app(current_runtime):
        current_runtime.startup_ready = True
        current_runtime.startup_error = None
        current_runtime.dispatcher = FakeDispatcher()

    monkeypatch.setattr(src.api.webhooks, "startup_web_app", fake_startup_web_app)

    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    payload = {"update_id": 999, "message": {"text": "/start"}}
    response = await async_client.post("/webhook", json=payload, headers=headers)

    assert response.status_code == 200
    assert dispatched_payloads == [payload]
