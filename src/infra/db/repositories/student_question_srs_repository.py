from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select

from src.infra.db.models.student_question_srs import StudentQuestionSrs
from src.infra.db.session import AsyncSessionLocal


class StudentQuestionSrsRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get(self, user_id: int, question_id: int) -> StudentQuestionSrs | None:
        async with self.session_factory() as session:
            return await self._get_record(session, user_id, question_id)

    async def get_many(
        self, user_id: int, question_ids: Iterable[int]
    ) -> dict[int, StudentQuestionSrs]:
        question_ids = list(question_ids)
        if not question_ids:
            return {}

        async with self.session_factory() as session:
            result = await session.execute(
                select(StudentQuestionSrs).where(
                    StudentQuestionSrs.user_id == user_id,
                    StudentQuestionSrs.question_id.in_(question_ids),
                )
            )
            records = result.scalars().all()
            return {record.question_id: record for record in records}

    async def upsert(
        self,
        *,
        user_id: int,
        course_id: str,
        question_id: int,
        box: int,
        last_presented_at=None,
        last_correct_at=None,
        last_transition_at=None,
    ) -> StudentQuestionSrs:
        async with self.session_factory() as session:
            record = await self._get_record(session, user_id, question_id)
            if record is None:
                record = StudentQuestionSrs(
                    user_id=user_id,
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
        self, session, user_id: int, question_id: int
    ) -> StudentQuestionSrs | None:
        result = await session.execute(
            select(StudentQuestionSrs).where(
                StudentQuestionSrs.user_id == user_id,
                StudentQuestionSrs.question_id == question_id,
            )
        )
        return result.scalar_one_or_none()
