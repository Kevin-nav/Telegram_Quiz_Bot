import pytest

from src.api.telegram_dispatcher import TelegramUpdateDispatcher


class FakeRuntime:
    pass


@pytest.mark.asyncio
async def test_dispatcher_classifies_callbacks_and_poll_answers_inline():
    dispatcher = TelegramUpdateDispatcher(FakeRuntime())

    assert dispatcher.classify({"callback_query": {"id": "1"}}) == "inline"
    assert dispatcher.classify({"callback_query": {"id": "1", "data": "report:start:question"}}) == "inline"
    assert dispatcher.classify({"poll_answer": {"poll_id": "1"}}) == "inline"
    assert dispatcher.classify({"message": {"text": "/start"}}) == "inline"
    assert dispatcher.classify({"message": {"text": "This answer key is wrong"}}) == "inline"


@pytest.mark.asyncio
async def test_dispatcher_classifies_non_text_messages_as_background():
    dispatcher = TelegramUpdateDispatcher(FakeRuntime())

    route = dispatcher.classify({"message": {"photo": [{"file_id": "abc"}]}})

    assert route == "background"


@pytest.mark.asyncio
async def test_dispatcher_can_force_all_updates_to_background():
    dispatcher = TelegramUpdateDispatcher(FakeRuntime(), force_background=True)

    assert dispatcher.classify({"callback_query": {"id": "1"}}) == "background"
    assert dispatcher.classify({"poll_answer": {"poll_id": "1"}}) == "background"
    assert dispatcher.classify({"message": {"text": "/start"}}) == "background"


@pytest.mark.asyncio
async def test_dispatcher_passes_bot_id_to_inline_processor(monkeypatch):
    processed = []

    async def fake_process_telegram_update(runtime, payload, *, bot_id="tanjah"):
        processed.append((runtime, payload, bot_id))

    monkeypatch.setattr(
        "src.api.telegram_dispatcher.process_telegram_update",
        fake_process_telegram_update,
    )

    runtime = FakeRuntime()
    dispatcher = TelegramUpdateDispatcher(runtime)

    await dispatcher._process_inline({"message": {"text": "/start"}}, bot_id="adarkwa")

    assert processed == [
        (
            runtime,
            {"message": {"text": "/start"}},
            "adarkwa",
        )
    ]
