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
                    total_correct=0,
                    avg_time_per_question=None,
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

    async def list_for_user(
        self,
        user_id: int,
        *,
        bot_id: str | None = None,
        course_codes: set[str] | None = None,
    ) -> list[StudentCourseState]:
        async with self.session_factory() as session:
            statement = select(StudentCourseState).where(StudentCourseState.user_id == user_id)
            if bot_id is not None:
                statement = statement.where(StudentCourseState.bot_id == bot_id)
            if course_codes is not None:
                if not course_codes:
                    return []
                statement = statement.where(StudentCourseState.course_id.in_(sorted(course_codes)))
            statement = statement.order_by(StudentCourseState.course_id.asc())
            result = await session.execute(statement)
            return list(result.scalars().all())

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

    async def record_attempt_metrics(
        self,
        user_id: int,
        course_id: str,
        *,
        bot_id: str | None = None,
        is_correct: bool,
        time_taken_seconds: float | None,
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
                    total_correct=0,
                    avg_time_per_question=None,
                )
                session.add(state)
                await session.flush()

            total_attempts = int(getattr(state, "total_attempts", 0) or 0)
            previous_avg_time = getattr(state, "avg_time_per_question", None)
            if is_correct:
                state.total_correct = int(getattr(state, "total_correct", 0) or 0) + 1
            if time_taken_seconds is not None:
                timed_attempt_count = max(total_attempts - 1, 0)
                if previous_avg_time is None or timed_attempt_count <= 0:
                    state.avg_time_per_question = float(time_taken_seconds)
                else:
                    aggregate = (float(previous_avg_time) * timed_attempt_count) + float(
                        time_taken_seconds
                    )
                    state.avg_time_per_question = round(
                        aggregate / (timed_attempt_count + 1),
                        1,
                    )

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
