import pytest


@pytest.mark.asyncio
async def test_bootstrap_initializes_shared_services():
    from src.app.bootstrap import create_app_state

    state = await create_app_state()

    assert state.settings is not None
    assert state.redis is not None
    assert state.telegram_app is not None
    assert state.arq_pool is None


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
    )

    await shutdown_web_app(state)

    assert dispatcher.shutdown_called is True
    assert telegram_app.stop_called is True
    assert telegram_app.shutdown_called is True
    assert close_called is True
    assert telegram_app.bot.delete_webhook_called is False
