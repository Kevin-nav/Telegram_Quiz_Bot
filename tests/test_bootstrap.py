import pytest


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
    )

    await startup_web_app(state)

    assert state.startup_ready is False
    assert state.startup_error == "redis_unavailable:RuntimeError"
    assert telegram_app.initialize_called is False
    assert telegram_app.start_called is False
    assert telegram_app.bot.set_webhook_called is False
    assert state.dispatcher is None


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
        startup_ready=True,
    )

    await shutdown_web_app(state)

    assert dispatcher.shutdown_called is True
    assert telegram_app.stop_called is True
    assert telegram_app.shutdown_called is True
    assert close_called is True
    assert telegram_app.bot.delete_webhook_called is False


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

    async def fake_close_arq_pool():
        return None

    monkeypatch.setattr("src.app.bootstrap.close_arq_pool", fake_close_arq_pool)

    telegram_app = DummyTelegramApp()
    state = SimpleNamespace(
        dispatcher=None,
        telegram_app=telegram_app,
        telegram_initialized=False,
        telegram_started=False,
        startup_ready=False,
    )

    await shutdown_web_app(state)

    assert telegram_app.stop_called is False
    assert telegram_app.shutdown_called is False
