import pytest
import asyncio


@pytest.mark.asyncio
async def test_bootstrap_initializes_shared_services():
    from src.app.bootstrap import create_app_state

    state = await create_app_state()

    assert state.settings is not None
    assert state.redis is not None
    assert state.telegram_app is not None
    assert state.arq_pool is None
    assert state.startup_ready is False
    assert state.dispatcher is None


@pytest.mark.asyncio
async def test_startup_web_app_marks_runtime_degraded_when_arq_init_fails(monkeypatch):
    from types import SimpleNamespace

    from src.app.bootstrap import startup_web_app

    class DummyBot:
        def __init__(self):
            self.set_webhook_called = False

        async def set_webhook(self, **kwargs):
            self.set_webhook_called = True

    class DummyTelegramApp:
        def __init__(self):
            self.bot = DummyBot()
            self.bot_data = {}
            self.initialize_called = False
            self.start_called = False

        async def initialize(self):
            self.initialize_called = True

        async def start(self):
            self.start_called = True

    async def fake_init_arq_pool():
        raise RuntimeError("redis offline")

    async def fake_set_bot_commands(_telegram_app):
        raise AssertionError("set_bot_commands should not run in degraded startup")

    monkeypatch.setattr("src.app.bootstrap.init_arq_pool", fake_init_arq_pool)
    monkeypatch.setattr("src.app.bootstrap.set_bot_commands", fake_set_bot_commands)

    telegram_app = DummyTelegramApp()
    state = SimpleNamespace(
        arq_pool=None,
        startup_ready=False,
        startup_error=None,
        telegram_app=telegram_app,
        settings=SimpleNamespace(
            webhook_url="https://example.com",
            webhook_secret="secret",
        ),
        dispatcher=None,
        telegram_initialized=False,
        telegram_started=False,
        webhook_registered=False,
        last_startup_attempt_at=None,
        startup_retry_interval_seconds=0,
    )

    await startup_web_app(state)

    assert state.startup_ready is False
    assert state.startup_error == "redis_unavailable:RuntimeError"
    assert telegram_app.initialize_called is False
    assert telegram_app.start_called is False
    assert telegram_app.bot.set_webhook_called is False
    assert state.dispatcher is None


@pytest.mark.asyncio
async def test_startup_web_app_recovers_after_subsequent_retry(monkeypatch):
    from types import SimpleNamespace

    from src.app.bootstrap import startup_web_app

    class DummyBot:
        def __init__(self):
            self.set_webhook_calls = []

        async def set_webhook(self, **kwargs):
            self.set_webhook_calls.append(kwargs)

    class DummyTelegramApp:
        def __init__(self):
            self.bot = DummyBot()
            self.bot_data = {}
            self.initialize_calls = 0
            self.start_calls = 0

        async def initialize(self):
            self.initialize_calls += 1

        async def start(self):
            self.start_calls += 1

    arq_attempts = {"count": 0}

    async def fake_init_arq_pool():
        arq_attempts["count"] += 1
        if arq_attempts["count"] == 1:
            raise RuntimeError("redis offline")
        return object()

    async def fake_set_bot_commands(_telegram_app):
        return None

    monkeypatch.setattr("src.app.bootstrap.init_arq_pool", fake_init_arq_pool)
    monkeypatch.setattr("src.app.bootstrap.set_bot_commands", fake_set_bot_commands)

    telegram_app = DummyTelegramApp()
    state = SimpleNamespace(
        arq_pool=None,
        startup_ready=False,
        startup_error=None,
        telegram_app=telegram_app,
        settings=SimpleNamespace(
            webhook_url="https://example.com",
            webhook_secret="secret",
        ),
        dispatcher=None,
        telegram_initialized=False,
        telegram_started=False,
        webhook_registered=False,
        last_startup_attempt_at=None,
        startup_retry_interval_seconds=0,
    )

    await startup_web_app(state)
    assert state.startup_ready is False

    await startup_web_app(state)

    assert state.startup_ready is True
    assert state.startup_error is None
    assert telegram_app.initialize_calls == 1
    assert telegram_app.start_calls == 1
    assert len(telegram_app.bot.set_webhook_calls) == 1
    assert state.dispatcher is not None


@pytest.mark.asyncio
async def test_startup_web_app_cleans_up_partial_telegram_startup(monkeypatch):
    from types import SimpleNamespace

    from src.app.bootstrap import startup_web_app

    class DummyDispatcher:
        def __init__(self, runtime):
            self.runtime = runtime
            self.shutdown_called = False

        async def shutdown(self):
            self.shutdown_called = True

    class DummyBot:
        def __init__(self):
            self.delete_webhook_called = False

        async def delete_webhook(self):
            self.delete_webhook_called = True

    class DummyTelegramApp:
        def __init__(self):
            self.bot = DummyBot()
            self.bot_data = {}
            self.initialize_calls = 0
            self.start_calls = 0
            self.stop_calls = 0
            self.shutdown_calls = 0

        async def initialize(self):
            self.initialize_calls += 1

        async def start(self):
            self.start_calls += 1

        async def stop(self):
            self.stop_calls += 1

        async def shutdown(self):
            self.shutdown_calls += 1

    async def fake_init_arq_pool():
        return object()

    async def fake_set_bot_commands(_telegram_app):
        raise RuntimeError("telegram commands failed")

    monkeypatch.setattr("src.app.bootstrap.init_arq_pool", fake_init_arq_pool)
    monkeypatch.setattr("src.app.bootstrap.set_bot_commands", fake_set_bot_commands)
    monkeypatch.setattr("src.app.bootstrap.TelegramUpdateDispatcher", DummyDispatcher)

    telegram_app = DummyTelegramApp()
    state = SimpleNamespace(
        arq_pool=None,
        startup_ready=False,
        startup_error=None,
        telegram_app=telegram_app,
        settings=SimpleNamespace(
            webhook_url="https://example.com",
            webhook_secret="secret",
        ),
        dispatcher=None,
        telegram_initialized=False,
        telegram_started=False,
        webhook_registered=False,
        last_startup_attempt_at=None,
        startup_retry_interval_seconds=0,
    )

    await startup_web_app(state)

    assert state.startup_ready is False
    assert state.startup_error == "telegram_startup_failed:RuntimeError"
    assert state.dispatcher is None
    assert telegram_app.bot_data.get("background_scheduler") is None
    assert telegram_app.stop_calls == 1
    assert telegram_app.shutdown_calls == 1
    assert state.telegram_started is False
    assert state.telegram_initialized is False
    assert state.webhook_registered is False
    assert telegram_app.bot.delete_webhook_called is False


@pytest.mark.asyncio
async def test_startup_web_app_serializes_concurrent_recovery(monkeypatch):
    from types import SimpleNamespace

    from src.app.bootstrap import startup_web_app

    class DummyBot:
        async def set_webhook(self, **kwargs):
            return None

    class DummyTelegramApp:
        def __init__(self):
            self.bot = DummyBot()
            self.bot_data = {}
            self.initialize_calls = 0
            self.start_calls = 0

        async def initialize(self):
            self.initialize_calls += 1

        async def start(self):
            self.start_calls += 1

    arq_attempts = {"count": 0}
    release_pool = asyncio.Event()

    async def fake_init_arq_pool():
        arq_attempts["count"] += 1
        await release_pool.wait()
        return object()

    async def fake_set_bot_commands(_telegram_app):
        return None

    monkeypatch.setattr("src.app.bootstrap.init_arq_pool", fake_init_arq_pool)
    monkeypatch.setattr("src.app.bootstrap.set_bot_commands", fake_set_bot_commands)

    telegram_app = DummyTelegramApp()
    state = SimpleNamespace(
        arq_pool=None,
        startup_ready=False,
        startup_error=None,
        telegram_app=telegram_app,
        settings=SimpleNamespace(
            webhook_url="https://example.com",
            webhook_secret="secret",
        ),
        dispatcher=None,
        telegram_initialized=False,
        telegram_started=False,
        webhook_registered=False,
        last_startup_attempt_at=None,
        startup_retry_interval_seconds=0,
    )

    task_one = asyncio.create_task(startup_web_app(state))
    await asyncio.sleep(0)
    task_two = asyncio.create_task(startup_web_app(state))
    await asyncio.sleep(0)
    release_pool.set()
    await asyncio.gather(task_one, task_two)

    assert arq_attempts["count"] == 1
    assert telegram_app.initialize_calls == 1
    assert telegram_app.start_calls == 1
    assert state.startup_ready is True


@pytest.mark.asyncio
async def test_shutdown_web_app_does_not_delete_webhook(monkeypatch):
    from types import SimpleNamespace

    from src.app.bootstrap import shutdown_web_app

    class DummyDispatcher:
        def __init__(self):
            self.shutdown_called = False

        async def shutdown(self):
            self.shutdown_called = True

    class DummyBot:
        def __init__(self):
            self.delete_webhook_called = False

        async def delete_webhook(self):
            self.delete_webhook_called = True

    class DummyTelegramApp:
        def __init__(self):
            self.bot = DummyBot()
            self.stop_called = False
            self.shutdown_called = False

        async def stop(self):
            self.stop_called = True

        async def shutdown(self):
            self.shutdown_called = True

    close_called = False

    async def fake_close_arq_pool():
        nonlocal close_called
        close_called = True

    monkeypatch.setattr("src.app.bootstrap.close_arq_pool", fake_close_arq_pool)

    dispatcher = DummyDispatcher()
    telegram_app = DummyTelegramApp()
    state = SimpleNamespace(
        dispatcher=dispatcher,
        settings=SimpleNamespace(webhook_url="https://tg-bot-tanjah.sankoslides.com"),
        telegram_app=telegram_app,
        telegram_initialized=True,
        telegram_started=True,
        webhook_registered=True,
        startup_ready=True,
        arq_pool=object(),
        last_startup_attempt_at=123.0,
    )

    await shutdown_web_app(state)

    assert dispatcher.shutdown_called is True
    assert telegram_app.stop_called is True
    assert telegram_app.shutdown_called is True
    assert close_called is True
    assert telegram_app.bot.delete_webhook_called is False
    assert state.arq_pool is None
    assert state.last_startup_attempt_at is None


@pytest.mark.asyncio
async def test_shutdown_web_app_skips_uninitialized_telegram_app(monkeypatch):
    from types import SimpleNamespace

    from src.app.bootstrap import shutdown_web_app

    class DummyTelegramApp:
        def __init__(self):
            self.bot = SimpleNamespace()
            self.stop_called = False
            self.shutdown_called = False

        async def stop(self):
            self.stop_called = True

        async def shutdown(self):
            self.shutdown_called = True

    close_calls = {"count": 0}

    async def fake_close_arq_pool():
        close_calls["count"] += 1

    monkeypatch.setattr("src.app.bootstrap.close_arq_pool", fake_close_arq_pool)

    telegram_app = DummyTelegramApp()
    state = SimpleNamespace(
        dispatcher=None,
        telegram_app=telegram_app,
        telegram_initialized=False,
        telegram_started=False,
        webhook_registered=False,
        startup_ready=False,
        arq_pool=object(),
        last_startup_attempt_at=None,
    )

    await shutdown_web_app(state)

    assert telegram_app.stop_called is False
    assert telegram_app.shutdown_called is False
    assert close_calls["count"] == 1
    assert state.arq_pool is None
