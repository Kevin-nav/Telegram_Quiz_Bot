from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select

from src.infra.db.models.student_question_srs import StudentQuestionSrs
from src.infra.db.session import AsyncSessionLocal


class StudentQuestionSrsRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get(
        self,
        user_id: int,
        question_id: int,
        *,
        bot_id: str | None = None,
    ) -> StudentQuestionSrs | None:
        async with self.session_factory() as session:
            return await self._get_record(session, user_id, question_id, bot_id=bot_id)

    async def get_many(
        self,
        user_id: int,
        question_ids: Iterable[int],
        *,
        bot_id: str | None = None,
    ) -> dict[int, StudentQuestionSrs]:
        question_ids = list(question_ids)
        if not question_ids:
            return {}

        async with self.session_factory() as session:
            statement = select(StudentQuestionSrs).where(
                StudentQuestionSrs.user_id == user_id,
                StudentQuestionSrs.question_id.in_(question_ids),
            )
            if bot_id is not None:
                statement = statement.where(StudentQuestionSrs.bot_id == bot_id)
            result = await session.execute(statement)
            records = result.scalars().all()
            return {record.question_id: record for record in records}

    async def upsert(
        self,
        *,
        user_id: int,
        bot_id: str | None = None,
        course_id: str,
        question_id: int,
        box: int,
        last_presented_at=None,
        last_correct_at=None,
        last_transition_at=None,
    ) -> StudentQuestionSrs:
        async with self.session_factory() as session:
            record = await self._get_record(session, user_id, question_id, bot_id=bot_id)
            if record is None:
                record = StudentQuestionSrs(
                    user_id=user_id,
                    bot_id=bot_id,
                    course_id=course_id,
                    question_id=question_id,
                    box=box,
                    last_presented_at=last_presented_at,
                    last_correct_at=last_correct_at,
                    last_transition_at=last_transition_at,
                )
                session.add(record)
            else:
                record.course_id = course_id
                record.box = box
                record.last_presented_at = last_presented_at
                record.last_correct_at = last_correct_at
                record.last_transition_at = last_transition_at

            await session.commit()
            await session.refresh(record)
            return record

    async def _get_record(
        self,
        session,
        user_id: int,
        question_id: int,
        *,
        bot_id: str | None = None,
    ) -> StudentQuestionSrs | None:
        statement = select(StudentQuestionSrs).where(
            StudentQuestionSrs.user_id == user_id,
            StudentQuestionSrs.question_id == question_id,
        )
        if bot_id is not None:
            statement = statement.where(StudentQuestionSrs.bot_id == bot_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()
