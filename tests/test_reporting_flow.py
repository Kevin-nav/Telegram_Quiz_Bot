from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.bot.handlers.reporting import handle_report_callback, handle_report_note_message
from src.domains.quiz.models import QuizQuestion, QuizSessionState
from src.domains.quiz.service import QuizSessionService
from src.domains.quiz_reporting.service import QuizReportingService
from src.infra.redis.state_store import InteractiveStateStore
from tests.fakes import FakeRedis


class FakeScheduledJob:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def close(self):
        self.closed = True


class FakeQuery:
    def __init__(self, data: str, *, message_id: int):
        self.data = data
        self.message = SimpleNamespace(message_id=message_id, chat=SimpleNamespace(id=77))
        self.calls = []
        self.answers = []
        self.cleared_reply_markup = 0

    async def answer(self, text=None, show_alert=False):
        self.answers.append({"text": text, "show_alert": show_alert})

    async def edit_message_text(self, text, reply_markup=None):
        self.calls.append({"text": text, "reply_markup": reply_markup})

    async def edit_message_reply_markup(self, reply_markup=None):
        self.cleared_reply_markup += 1


class FakeMessage:
    def __init__(self, text: str):
        self.text = text
        self.reply_calls = []

    async def reply_text(self, text, reply_markup=None):
        self.reply_calls.append({"text": text, "reply_markup": reply_markup})


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def schedule_coroutine(self, coro):
        self.jobs.append(coro)
        close = getattr(coro, "close", None)
        if close is not None:
            close()


def _make_context(store: InteractiveStateStore, scheduler: FakeScheduler):
    quiz_service = QuizSessionService(state_store=store)
    return SimpleNamespace(
        application=SimpleNamespace(
            bot_data={
                "quiz_session_service": quiz_service,
                "quiz_reporting_service": QuizReportingService(),
                "background_scheduler": scheduler,
            }
        ),
        user_data={},
    )


async def _seed_session(store: InteractiveStateStore):
    session = QuizSessionState(
        session_id="session-1",
        user_id=42,
        chat_id=77,
        course_id="linear-electronics",
        course_name="Linear Electronics",
        questions=[
            QuizQuestion(
                question_id="q1",
                source_question_id=17,
                prompt="Question 1",
                options=["A", "B"],
                correct_option_id=1,
                explanation="Because B is correct.",
            )
        ],
        current_index=0,
        question_action_message_id=201,
        answer_action_message_id=202,
        last_answered_question_id="q1",
        last_answered_question_index=0,
    )
    await store.set_quiz_session(session)
    await store.set_active_quiz(42, "session-1")


@pytest.mark.asyncio
async def test_report_start_callback_shows_reason_picker_for_active_message():
    store = InteractiveStateStore(FakeRedis())
    scheduler = FakeScheduler()
    context = _make_context(store, scheduler)
    await _seed_session(store)
    query = FakeQuery("report:start:question", message_id=201)
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=42))

    await handle_report_callback(update, context)

    assert "what is wrong with this question" in query.calls[-1]["text"].lower()


@pytest.mark.asyncio
async def test_report_reason_selection_stores_pending_note_state():
    store = InteractiveStateStore(FakeRedis())
    scheduler = FakeScheduler()
    context = _make_context(store, scheduler)
    await _seed_session(store)
    query = FakeQuery("report:reason:answer:explanation_is_wrong", message_id=202)
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=42))

    await handle_report_callback(update, context)

    pending = await store.get_pending_report_note(42)
    assert pending is not None
    assert pending["report_scope"] == "answer"
    assert pending["report_reason"] == "explanation_is_wrong"
    assert "send any extra detail" in query.calls[-1]["text"].lower()


@pytest.mark.asyncio
async def test_stale_report_callback_is_rejected_and_keyboard_is_cleared():
    store = InteractiveStateStore(FakeRedis())
    scheduler = FakeScheduler()
    context = _make_context(store, scheduler)
    await _seed_session(store)
    query = FakeQuery("report:start:question", message_id=999)
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=42))

    await handle_report_callback(update, context)

    assert query.answers[-1]["text"] == "This report menu is out of date. Use the latest one."
    assert query.cleared_reply_markup == 1
    assert not query.calls


@pytest.mark.asyncio
async def test_report_callback_is_rejected_when_active_report_buttons_are_invalidated():
    store = InteractiveStateStore(FakeRedis())
    scheduler = FakeScheduler()
    context = _make_context(store, scheduler)
    await _seed_session(store)
    session = await store.get_quiz_session("session-1")
    session.question_action_message_id = None
    await store.set_quiz_session(session)
    query = FakeQuery("report:start:question", message_id=201)
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=42))

    await handle_report_callback(update, context)

    assert query.answers[-1]["text"] == "This report menu is out of date. Use the latest one."
    assert query.cleared_reply_markup == 1
    assert not query.calls


@pytest.mark.asyncio
async def test_report_note_message_persists_report_and_clears_pending_state(monkeypatch):
    store = InteractiveStateStore(FakeRedis())
    scheduler = FakeScheduler()
    context = _make_context(store, scheduler)
    await _seed_session(store)
    payload = {
        "user_id": 42,
        "session_id": "session-1",
        "course_id": "linear-electronics",
        "question_id": 17,
        "question_key": "q1",
        "question_index": 0,
        "report_scope": "answer",
        "report_reason": "correct_answer_shown_is_wrong",
        "report_note": None,
        "report_metadata": {"correct_option_text": "B"},
    }
    await store.set_pending_report_note(42, payload)
    await store.set_report_draft(42, payload)

    jobs: list[FakeScheduledJob] = []

    def fake_enqueue(payload):
        job = FakeScheduledJob(payload)
        jobs.append(job)
        return job

    import src.bot.handlers.reporting as reporting_module

    monkeypatch.setattr(reporting_module, "enqueue_persist_question_report", fake_enqueue)

    message = FakeMessage("This should be option B.")
    update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_message=message)

    await handle_report_note_message(update, context)

    assert jobs
    assert jobs[0].payload["report_note"] == "This should be option B."
    assert await store.get_pending_report_note(42) is None
    assert await store.get_report_draft(42) is None
    assert "thanks" in message.reply_calls[-1]["text"].lower()
