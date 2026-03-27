from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select

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
            if limit is not None:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def list_attempts_for_questions(
        self,
        *,
        user_id: int,
        question_ids: Iterable[int],
    ) -> dict[int, list[QuestionAttempt]]:
        question_ids = list(question_ids)
        if not question_ids:
            return {}

        async with self.session_factory() as session:
            result = await session.execute(
                select(QuestionAttempt)
                .where(
                    QuestionAttempt.user_id == user_id,
                    QuestionAttempt.question_id.in_(question_ids),
                )
                .order_by(QuestionAttempt.created_at.asc(), QuestionAttempt.id.asc())
            )
            grouped: dict[int, list[QuestionAttempt]] = defaultdict(list)
            for attempt in result.scalars().all():
                grouped[attempt.question_id].append(attempt)
            return dict(grouped)

    async def list_attempts_for_user(
        self,
        *,
        user_id: int,
        limit: int | None = None,
    ) -> list[QuestionAttempt]:
        async with self.session_factory() as session:
            statement = (
                select(QuestionAttempt)
                .where(QuestionAttempt.user_id == user_id)
                .order_by(QuestionAttempt.created_at.desc(), QuestionAttempt.id.desc())
            )
            if limit is not None:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())
