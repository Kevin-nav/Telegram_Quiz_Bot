from collections import defaultdict
from collections.abc import Iterable
from types import SimpleNamespace

from sqlalchemy import case, func, select

from src.infra.db.models.question_attempt import QuestionAttempt
from src.infra.db.session import AsyncSessionLocal


class QuestionAttemptRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def create_attempt(self, payload: dict) -> QuestionAttempt:
        async with self.session_factory() as session:
            attempt = QuestionAttempt(**payload)
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)
            return attempt

    async def list_attempts_for_question(
        self,
        *,
        user_id: int,
        question_id: int,
        bot_id: str | None = None,
        limit: int | None = None,
    ) -> list[QuestionAttempt]:
        async with self.session_factory() as session:
            statement = (
                select(QuestionAttempt)
                .where(
                    QuestionAttempt.user_id == user_id,
                    QuestionAttempt.question_id == question_id,
                )
                .order_by(QuestionAttempt.created_at.asc(), QuestionAttempt.id.asc())
            )
            if bot_id is not None:
                statement = statement.where(QuestionAttempt.bot_id == bot_id)
            if limit is not None:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def list_attempts_for_questions(
        self,
        *,
        user_id: int,
        question_ids: Iterable[int],
        bot_id: str | None = None,
    ) -> dict[int, list[QuestionAttempt]]:
        question_ids = list(question_ids)
        if not question_ids:
            return {}

        async with self.session_factory() as session:
            statement = (
                select(QuestionAttempt)
                .where(
                    QuestionAttempt.user_id == user_id,
                    QuestionAttempt.question_id.in_(question_ids),
                )
                .order_by(QuestionAttempt.created_at.asc(), QuestionAttempt.id.asc())
            )
            if bot_id is not None:
                statement = statement.where(QuestionAttempt.bot_id == bot_id)
            result = await session.execute(statement)
            grouped: dict[int, list[QuestionAttempt]] = defaultdict(list)
            for attempt in result.scalars().all():
                grouped[attempt.question_id].append(attempt)
            return dict(grouped)

    async def summarize_attempts_for_questions(
        self,
        *,
        user_id: int,
        question_ids: Iterable[int],
        bot_id: str | None = None,
    ) -> dict[int, object]:
        question_ids = list(question_ids)
        if not question_ids:
            return {}

        async with self.session_factory() as session:
            wrong_attempt_case = case((QuestionAttempt.is_correct.is_(False), 1), else_=0)
            last_wrong_at_case = case(
                (QuestionAttempt.is_correct.is_(False), QuestionAttempt.created_at),
                else_=None,
            )
            statement = (
                select(
                    QuestionAttempt.question_id,
                    func.count(QuestionAttempt.id),
                    func.sum(wrong_attempt_case),
                    func.max(last_wrong_at_case),
                )
                .where(
                    QuestionAttempt.user_id == user_id,
                    QuestionAttempt.question_id.in_(question_ids),
                )
                .group_by(QuestionAttempt.question_id)
            )
            if bot_id is not None:
                statement = statement.where(QuestionAttempt.bot_id == bot_id)
            result = await session.execute(statement)
            return {
                int(question_id): SimpleNamespace(
                    total_attempts=int(total_attempts or 0),
                    wrong_attempts=int(wrong_attempts or 0),
                    last_wrong_at=last_wrong_at,
                )
                for question_id, total_attempts, wrong_attempts, last_wrong_at in result.all()
            }

    async def list_attempts_for_user(
        self,
        *,
        user_id: int,
        bot_id: str | None = None,
        limit: int | None = None,
    ) -> list[QuestionAttempt]:
        async with self.session_factory() as session:
            statement = (
                select(QuestionAttempt)
                .where(QuestionAttempt.user_id == user_id)
                .order_by(QuestionAttempt.created_at.desc(), QuestionAttempt.id.desc())
            )
            if bot_id is not None:
                statement = statement.where(QuestionAttempt.bot_id == bot_id)
            if limit is not None:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())
