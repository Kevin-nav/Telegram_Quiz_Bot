from types import SimpleNamespace

import pytest

from src.domains.quiz.service import QuizSessionService
from src.infra.redis.state_store import InteractiveStateStore
from tests.fakes import FakeRedis


class FakeBot:
    def __init__(self):
        self.poll_calls = []
        self.message_calls = []

    async def send_poll(
        self,
        *,
        chat_id,
        question,
        options,
        type,
        is_anonymous,
        correct_option_id,
    ):
        poll_id = f"poll-{len(self.poll_calls) + 1}"
        self.poll_calls.append(
            {
                "chat_id": chat_id,
                "question": question,
                "options": options,
                "type": type,
                "is_anonymous": is_anonymous,
                "correct_option_id": correct_option_id,
                "poll_id": poll_id,
            }
        )
        return SimpleNamespace(poll=SimpleNamespace(id=poll_id))

    async def send_message(self, *, chat_id, text):
        self.message_calls.append({"chat_id": chat_id, "text": text})


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def __call__(self, coro):
        self.jobs.append(coro)
        coro.close()


@pytest.mark.asyncio
async def test_start_quiz_creates_state_and_sends_first_poll():
    store = InteractiveStateStore(FakeRedis())
    service = QuizSessionService(state_store=store)
    bot = FakeBot()
    scheduler = FakeScheduler()

    session = await service.start_quiz(
        bot=bot,
        user_id=42,
        chat_id=99,
        course_id="calculus",
        course_name="Calculus",
        question_count=2,
        schedule_background=scheduler,
    )

    active_session = await store.get_active_quiz(42)
    loaded_session = await store.get_quiz_session(session.session_id)

    assert active_session == session.session_id
    assert loaded_session is not None
    assert loaded_session.current_poll_id == "poll-1"
    assert bot.poll_calls


@pytest.mark.asyncio
async def test_poll_answer_advances_quiz_without_db_dependency():
    store = InteractiveStateStore(FakeRedis())
    service = QuizSessionService(state_store=store)
    bot = FakeBot()
    scheduler = FakeScheduler()

    session = await service.start_quiz(
        bot=bot,
        user_id=42,
        chat_id=99,
        course_id="calculus",
        course_name="Calculus",
        question_count=2,
        schedule_background=scheduler,
    )
    first_question = session.questions[0]

    handled = await service.handle_poll_answer(
        bot=bot,
        poll_answer=SimpleNamespace(
            poll_id="poll-1",
            option_ids=[first_question.correct_option_id],
        ),
        schedule_background=scheduler,
    )

    loaded_session = await store.get_quiz_session(session.session_id)

    assert handled is True
    assert loaded_session is not None
    assert loaded_session.current_index == 1
    assert loaded_session.current_poll_id == "poll-2"
    assert len(bot.poll_calls) == 2
