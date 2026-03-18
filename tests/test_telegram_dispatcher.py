import pytest

from src.api.telegram_dispatcher import TelegramUpdateDispatcher


class FakeRuntime:
    pass


@pytest.mark.asyncio
async def test_dispatcher_classifies_callbacks_and_poll_answers_inline():
    dispatcher = TelegramUpdateDispatcher(FakeRuntime())

    assert dispatcher.classify({"callback_query": {"id": "1"}}) == "inline"
    assert dispatcher.classify({"poll_answer": {"poll_id": "1"}}) == "inline"
    assert dispatcher.classify({"message": {"text": "/start"}}) == "inline"


@pytest.mark.asyncio
async def test_dispatcher_classifies_non_text_messages_as_background():
    dispatcher = TelegramUpdateDispatcher(FakeRuntime())

    route = dispatcher.classify({"message": {"photo": [{"file_id": "abc"}]}})

    assert route == "background"
