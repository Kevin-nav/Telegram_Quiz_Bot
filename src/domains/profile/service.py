from dataclasses import asdict
from types import SimpleNamespace

from sqlalchemy import select

from src.bot.runtime_config import TANJAH_BOT_ID
from src.infra.db.models.user_bot_profile import UserBotProfile
from src.infra.db.models.user import User
from src.infra.db.session import AsyncSessionLocal
from src.infra.redis.state_store import InteractiveStateStore, UserProfileRecord
from src.tasks.arq_client import enqueue_rebuild_profile_cache


class ProfileService:
    def __init__(
        self,
        session_factory=AsyncSessionLocal,
        state_store: InteractiveStateStore | None = None,
        bot_id: str = TANJAH_BOT_ID,
    ):
        self.session_factory = session_factory
        self.state_store = state_store
        self.bot_id = getattr(state_store, "bot_id", None) or bot_id

    def set_state_store(self, state_store: InteractiveStateStore) -> None:
        self.state_store = state_store
        self.bot_id = getattr(state_store, "bot_id", None) or self.bot_id

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
                await self._cache_user(user, None)
                return self._merge_user_profile(user, None)

            if display_name and user.display_name != display_name:
                user.display_name = display_name
                await session.commit()
                await session.refresh(user)

            profile = await self._get_profile(session, telegram_user_id)
            await self._cache_user(user, profile)
            return self._merge_user_profile(user, profile)

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
            user = await self._get_or_create_user(session, telegram_user_id)
            profile = await self._get_or_create_profile(session, telegram_user_id)

            if faculty_code is not None:
                profile.faculty_code = faculty_code
            if program_code is not None:
                profile.program_code = program_code
            if level_code is not None:
                profile.level_code = level_code
            if semester_code is not None:
                profile.semester_code = semester_code
            if preferred_course_code is not None:
                profile.preferred_course_code = preferred_course_code

            await session.commit()
            await session.refresh(user)
            await session.refresh(profile)
            await self._cache_user(user, profile)
            return self._merge_user_profile(user, profile)

    async def mark_onboarding_complete(self, telegram_user_id: int) -> User:
        async with self.session_factory() as session:
            user = await self._get_or_create_user(session, telegram_user_id)
            profile = await self._get_or_create_profile(session, telegram_user_id)
            profile.onboarding_completed = True
            await session.commit()
            await session.refresh(user)
            await session.refresh(profile)
            await self._cache_user(user, profile)
            return self._merge_user_profile(user, profile)

    async def rebuild_cache(self, telegram_user_id: int) -> None:
        if self.state_store is None:
            return

        async with self.session_factory() as session:
            user = await session.get(User, telegram_user_id)
            if user is None:
                await self.state_store.invalidate_user_profile(telegram_user_id)
                return

            profile = await self._get_profile(session, telegram_user_id)
            await self._cache_user(user, profile)

    async def persist_profile_record(self, payload: dict) -> User:
        telegram_user_id = payload["user_id"]

        async with self.session_factory() as session:
            user = await self._get_or_create_user(session, telegram_user_id)
            profile = await self._get_or_create_profile(session, telegram_user_id)

            if "display_name" in payload:
                user.display_name = payload.get("display_name")
            if "faculty_code" in payload:
                profile.faculty_code = payload.get("faculty_code")
            if "program_code" in payload:
                profile.program_code = payload.get("program_code")
            if "level_code" in payload:
                profile.level_code = payload.get("level_code")
            if "semester_code" in payload:
                profile.semester_code = payload.get("semester_code")
            if "preferred_course_code" in payload:
                profile.preferred_course_code = payload.get("preferred_course_code")
            if "onboarding_completed" in payload:
                profile.onboarding_completed = bool(payload.get("onboarding_completed"))

            await session.commit()
            await session.refresh(user)
            await session.refresh(profile)
            await self._cache_user(user, profile)
            return self._merge_user_profile(user, profile)

    async def _cache_user(self, user, profile: UserBotProfile | None) -> None:
        if self.state_store is None:
            return

        has_active_quiz = await self.state_store.has_active_quiz(user.id)
        await self.state_store.set_user_profile(
            self._build_profile_record(user, profile, has_active_quiz=has_active_quiz)
        )

    def _build_user_like(self, profile: UserProfileRecord):
        return SimpleNamespace(**asdict(profile))

    def _build_profile_record(
        self,
        user,
        profile: UserBotProfile | None,
        *,
        has_active_quiz: bool,
    ) -> UserProfileRecord:
        return UserProfileRecord(
            id=user.id,
            display_name=getattr(user, "display_name", None),
            faculty_code=getattr(profile, "faculty_code", None),
            program_code=getattr(profile, "program_code", None),
            level_code=getattr(profile, "level_code", None),
            semester_code=getattr(profile, "semester_code", None),
            preferred_course_code=getattr(profile, "preferred_course_code", None),
            onboarding_completed=bool(getattr(profile, "onboarding_completed", False)),
            has_active_quiz=has_active_quiz,
        )

    def _merge_user_profile(self, user, profile: UserBotProfile | None):
        return self._build_user_like(
            self._build_profile_record(user, profile, has_active_quiz=False)
        )

    async def _get_or_create_user(self, session, telegram_user_id: int) -> User:
        user = await session.get(User, telegram_user_id)
        if user is None:
            user = User(id=telegram_user_id, onboarding_completed=False)
            session.add(user)
            await session.flush()
        return user

    async def _get_profile(self, session, telegram_user_id: int) -> UserBotProfile | None:
        result = await session.execute(
            select(UserBotProfile).where(
                UserBotProfile.user_id == telegram_user_id,
                UserBotProfile.bot_id == self.bot_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_or_create_profile(self, session, telegram_user_id: int) -> UserBotProfile:
        profile = await self._get_profile(session, telegram_user_id)
        if profile is None:
            profile = UserBotProfile(
                user_id=telegram_user_id,
                bot_id=self.bot_id,
                onboarding_completed=False,
            )
            session.add(profile)
            await session.flush()
        return profile

    def _enqueue_profile_cache_rebuild(self, user_id: int) -> None:
        try:
            import asyncio

            asyncio.create_task(
                enqueue_rebuild_profile_cache(
                    {"user_id": user_id, "bot_id": self.bot_id}
                )
            )
        except RuntimeError:
            return
