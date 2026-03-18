from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from src.tasks.arq_client import enqueue_telegram_update
from src.workers.telegram_update import process_telegram_update


logger = logging.getLogger(__name__)


class TelegramUpdateDispatcher:
    def __init__(self, runtime, *, inline_capacity: int = 100):
        self.runtime = runtime
        self.inline_capacity = inline_capacity
        self._semaphore = asyncio.BoundedSemaphore(inline_capacity)
        self._tasks: set[asyncio.Task] = set()

    async def dispatch(self, payload: dict) -> str:
        route = self.classify(payload)
        if route == "inline":
            self.schedule_coroutine(self._process_inline(payload))
            return route

        await enqueue_telegram_update(payload)
        return route

    def classify(self, payload: dict) -> str:
        if payload.get("callback_query") is not None:
            return "inline"
        if payload.get("poll_answer") is not None:
            return "inline"

        message = payload.get("message") or payload.get("edited_message")
        if message is None:
            return "background"

        if message.get("text"):
            return "inline"

        return "background"

    def schedule_coroutine(self, coro) -> None:
        task = asyncio.create_task(self._run_bounded(coro))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        task.add_done_callback(self._log_task_failure)

    async def shutdown(self) -> None:
        if not self._tasks:
            return

        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()

        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

    async def _run_bounded(self, coro) -> None:
        async with self._semaphore:
            await coro

    async def _process_inline(self, payload: dict) -> None:
        await process_telegram_update(self.runtime, payload)

    def _log_task_failure(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            logger.exception("Inline Telegram task failed.", exc_info=exception)
