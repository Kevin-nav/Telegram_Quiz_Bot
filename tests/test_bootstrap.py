import pytest


@pytest.mark.asyncio
async def test_bootstrap_initializes_shared_services():
    from src.app.bootstrap import create_app_state

    state = await create_app_state()

    assert state.settings is not None
    assert state.redis is not None
    assert state.telegram_app is not None
    assert state.arq_pool is None
