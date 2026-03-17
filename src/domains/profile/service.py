from src.infra.db.models.user import User
from src.infra.db.session import AsyncSessionLocal


class ProfileService:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def load_or_initialize_user(
        self, telegram_user_id: int, display_name: str | None = None
    ) -> User:
        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                user = User(id=telegram_user_id, display_name=display_name)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                return user

            if display_name and user.display_name != display_name:
                user.display_name = display_name
                await session.commit()
                await session.refresh(user)

            return user

    async def update_study_profile(
        self,
        telegram_user_id: int,
        *,
        faculty_code: str | None = None,
        program_code: str | None = None,
        level_code: str | None = None,
        semester_code: str | None = None,
        preferred_course_code: str | None = None,
    ) -> User:
        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                user = User(id=telegram_user_id)
                session.add(user)

            if faculty_code is not None:
                user.faculty_code = faculty_code
            if program_code is not None:
                user.program_code = program_code
            if level_code is not None:
                user.level_code = level_code
            if semester_code is not None:
                user.semester_code = semester_code
            if preferred_course_code is not None:
                user.preferred_course_code = preferred_course_code

            await session.commit()
            await session.refresh(user)
            return user

    async def mark_onboarding_complete(self, telegram_user_id: int) -> User:
        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                user = User(id=telegram_user_id)
                session.add(user)

            user.onboarding_completed = True
            await session.commit()
            await session.refresh(user)
            return user
