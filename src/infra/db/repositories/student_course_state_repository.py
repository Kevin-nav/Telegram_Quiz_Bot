from __future__ import annotations

from src.infra.db.models.student_course_state import StudentCourseState
from src.infra.db.session import AsyncSessionLocal
from sqlalchemy import select


class StudentCourseStateRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get(
        self,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
    ) -> StudentCourseState | None:
        async with self.session_factory() as session:
            return await self._get_state(session, user_id, course_id, bot_id=bot_id)

    async def get_or_create(
        self,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
    ) -> StudentCourseState:
        async with self.session_factory() as session:
            state = await self._get_state(session, user_id, course_id, bot_id=bot_id)
            if state is None:
                state = StudentCourseState(
                    user_id=user_id,
                    bot_id=bot_id,
                    course_id=course_id,
                    overall_skill=2.5,
                    topic_skills={},
                    cognitive_profile={},
                    processing_profile={},
                    misconception_flags=[],
                    phase="cold_start",
                    total_quizzes_completed=0,
                    total_attempts=0,
                )
                session.add(state)
            await session.commit()
            await session.refresh(state)
            return state

    async def update_fields(
        self,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
        **updates,
    ) -> StudentCourseState | None:
        async with self.session_factory() as session:
            state = await self._get_state(session, user_id, course_id, bot_id=bot_id)
            if state is None:
                return None

            self._apply_updates(state, updates)
            await session.commit()
            await session.refresh(state)
            return state

    async def increment_counters(
        self,
        user_id: int,
        course_id: str,
        bot_id: str | None = None,
        *,
        quizzes: int = 0,
        attempts: int = 0,
    ) -> StudentCourseState | None:
        async with self.session_factory() as session:
            state = await self._get_state(session, user_id, course_id, bot_id=bot_id)
            if state is None:
                return None

            state.total_quizzes_completed += quizzes
            state.total_attempts += attempts
            await session.commit()
            await session.refresh(state)
            return state

    async def _get_state(
        self,
        session,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
    ) -> StudentCourseState | None:
        statement = select(StudentCourseState).where(
            StudentCourseState.user_id == user_id,
            StudentCourseState.course_id == course_id,
        )
        if bot_id is not None:
            statement = statement.where(StudentCourseState.bot_id == bot_id)
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    def _apply_updates(self, state: StudentCourseState, updates: dict) -> None:
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
