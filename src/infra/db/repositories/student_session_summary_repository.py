from __future__ import annotations

from sqlalchemy import select

from src.infra.db.models.student_session_summary import StudentSessionSummary
from src.infra.db.session import AsyncSessionLocal


class StudentSessionSummaryRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get_by_session_id(
        self,
        session_id: str,
        *,
        bot_id: str | None = None,
    ) -> StudentSessionSummary | None:
        async with self.session_factory() as session:
            return await self._get_by_session_id(session, session_id, bot_id=bot_id)

    async def list_for_user(
        self,
        user_id: int,
        *,
        bot_id: str | None = None,
        course_codes: set[str] | None = None,
        limit: int | None = None,
    ) -> list[StudentSessionSummary]:
        async with self.session_factory() as session:
            statement = select(StudentSessionSummary).where(
                StudentSessionSummary.user_id == user_id
            )
            if bot_id is not None:
                statement = statement.where(StudentSessionSummary.bot_id == bot_id)
            if course_codes is not None:
                if not course_codes:
                    return []
                statement = statement.where(
                    StudentSessionSummary.course_id.in_(sorted(course_codes))
                )
            statement = statement.order_by(
                StudentSessionSummary.completed_at.desc(),
                StudentSessionSummary.id.desc(),
            )
            if limit is not None:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def upsert_summary(
        self,
        *,
        session_id: str,
        user_id: int,
        course_id: str,
        bot_id: str | None = None,
        total_questions: int,
        correct_count: int,
        avg_time_seconds: float | None,
        completed_at,
    ) -> StudentSessionSummary:
        async with self.session_factory() as session:
            summary = await self._get_by_session_id(session, session_id, bot_id=bot_id)
            incorrect_count = max(0, total_questions - correct_count)
            accuracy_percent = round((correct_count / total_questions) * 100, 1) if total_questions else 0.0
            if summary is None:
                summary = StudentSessionSummary(
                    session_id=session_id,
                    user_id=user_id,
                    course_id=course_id,
                    bot_id=bot_id,
                    total_questions=total_questions,
                    correct_count=correct_count,
                    incorrect_count=incorrect_count,
                    accuracy_percent=accuracy_percent,
                    avg_time_seconds=avg_time_seconds,
                    completed_at=completed_at,
                )
                session.add(summary)
            else:
                summary.user_id = user_id
                summary.course_id = course_id
                summary.total_questions = total_questions
                summary.correct_count = correct_count
                summary.incorrect_count = incorrect_count
                summary.accuracy_percent = accuracy_percent
                summary.avg_time_seconds = avg_time_seconds
                summary.completed_at = completed_at

            await session.commit()
            await session.refresh(summary)
            return summary

    async def _get_by_session_id(
        self,
        session,
        session_id: str,
        *,
        bot_id: str | None = None,
    ) -> StudentSessionSummary | None:
        statement = select(StudentSessionSummary).where(
            StudentSessionSummary.session_id == session_id
        )
        if bot_id is not None:
            statement = statement.where(StudentSessionSummary.bot_id == bot_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()
