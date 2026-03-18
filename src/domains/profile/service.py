from dataclasses import asdict
from types import SimpleNamespace

from src.infra.db.models.user import User
from src.infra.db.session import AsyncSessionLocal
from src.infra.redis.state_store import InteractiveStateStore, UserProfileRecord
from src.tasks.arq_client import enqueue_rebuild_profile_cache


class ProfileService:
    def __init__(
        self,
        session_factory=AsyncSessionLocal,
        state_store: InteractiveStateStore | None = None,
    ):
        self.session_factory = session_factory
        self.state_store = state_store

    def set_state_store(self, state_store: InteractiveStateStore) -> None:
        self.state_store = state_store

    async def load_or_initialize_user(
        self, telegram_user_id: int, display_name: str | None = None
    ) -> User:
        if self.state_store is not None:
            cached_profile = await self.state_store.get_user_profile(telegram_user_id)
            if cached_profile is not None:
                if display_name and cached_profile.display_name != display_name:
                    cached_profile.display_name = display_name
                    await self.state_store.set_user_profile(cached_profile)
                    self._enqueue_profile_cache_rebuild(cached_profile.id)
                return self._build_user_like(cached_profile)

        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                user = User(
                    id=telegram_user_id,
                    display_name=display_name,
                    onboarding_completed=False,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                await self._cache_user(user)
                return user

            if display_name and user.display_name != display_name:
                user.display_name = display_name
                await session.commit()
                await session.refresh(user)

            await self._cache_user(user)
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
                user = User(id=telegram_user_id, onboarding_completed=False)
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
            await self._cache_user(user)
            return user

    async def mark_onboarding_complete(self, telegram_user_id: int) -> User:
        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                user = User(id=telegram_user_id, onboarding_completed=False)
                session.add(user)

            user.onboarding_completed = True
            await session.commit()
            await session.refresh(user)
            await self._cache_user(user)
            return user

    async def rebuild_cache(self, telegram_user_id: int) -> None:
        if self.state_store is None:
            return

        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                await self.state_store.invalidate_user_profile(telegram_user_id)
                return

            await self._cache_user(user)

    async def persist_profile_record(self, payload: dict) -> User:
        telegram_user_id = payload["user_id"]

        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                user = User(id=telegram_user_id, onboarding_completed=False)
                session.add(user)

            if "display_name" in payload:
                user.display_name = payload.get("display_name")
            if "faculty_code" in payload:
                user.faculty_code = payload.get("faculty_code")
            if "program_code" in payload:
                user.program_code = payload.get("program_code")
            if "level_code" in payload:
                user.level_code = payload.get("level_code")
            if "semester_code" in payload:
                user.semester_code = payload.get("semester_code")
            if "preferred_course_code" in payload:
                user.preferred_course_code = payload.get("preferred_course_code")
            if "onboarding_completed" in payload:
                user.onboarding_completed = bool(payload.get("onboarding_completed"))

            await session.commit()
            await session.refresh(user)
            await self._cache_user(user)
            return user

    async def _cache_user(self, user) -> None:
        if self.state_store is None:
            return

        has_active_quiz = await self.state_store.has_active_quiz(user.id)
        await self.state_store.set_user_profile(
            UserProfileRecord.from_user(user, has_active_quiz=has_active_quiz)
        )

    def _build_user_like(self, profile: UserProfileRecord):
        return SimpleNamespace(**asdict(profile))

    def _enqueue_profile_cache_rebuild(self, user_id: int) -> None:
        try:
            import asyncio

            asyncio.create_task(enqueue_rebuild_profile_cache({"user_id": user_id}))
        except RuntimeError:
            return
