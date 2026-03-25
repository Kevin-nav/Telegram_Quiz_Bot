from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass

from src.domains.quiz.models import PollMapRecord, QuizQuestion, QuizSessionState
from src.infra.redis.keys import (
    active_quiz_key,
    adaptive_snapshot_key,
    adaptive_update_lock_key,
    analytics_dedupe_key,
    poll_map_key,
    question_bank_cache_key,
    quiz_session_key,
    quiz_session_lock_key,
    telegram_update_key,
    user_profile_key,
)


USER_PROFILE_TTL_SECONDS = 30 * 60
ACTIVE_QUIZ_TTL_SECONDS = 24 * 60 * 60
QUIZ_SESSION_TTL_SECONDS = 24 * 60 * 60
POLL_MAP_TTL_SECONDS = 60 * 60
LOCK_TTL_SECONDS = 15
ADAPTIVE_SNAPSHOT_TTL_SECONDS = 10 * 60
CATALOG_LOOKUP_TTL_SECONDS = 60 * 60


@dataclass(slots=True)
class UserProfileRecord:
    id: int
    display_name: str | None = None
    faculty_code: str | None = None
    program_code: str | None = None
    level_code: str | None = None
    semester_code: str | None = None
    preferred_course_code: str | None = None
    onboarding_completed: bool = False
    has_active_quiz: bool = False

    @classmethod
    def from_user(cls, user, *, has_active_quiz: bool = False) -> "UserProfileRecord":
        return cls(
            id=user.id,
            display_name=getattr(user, "display_name", None),
            faculty_code=getattr(user, "faculty_code", None),
            program_code=getattr(user, "program_code", None),
            level_code=getattr(user, "level_code", None),
            semester_code=getattr(user, "semester_code", None),
            preferred_course_code=getattr(user, "preferred_course_code", None),
            onboarding_completed=bool(getattr(user, "onboarding_completed", False)),
            has_active_quiz=has_active_quiz,
        )

    @classmethod
    def from_dict(cls, payload: dict) -> "UserProfileRecord":
        return cls(**payload)

    def to_dict(self) -> dict:
        return asdict(self)


class InteractiveStateStore:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self._local_cache: dict[str, tuple[float, object]] = {}
        self._catalog_cache_keys: set[str] = set()

    async def claim_update(self, update_id: int, ttl_seconds: int = 300) -> bool:
        result = await self.redis_client.set(
            telegram_update_key(update_id),
            "1",
            ex=ttl_seconds,
            nx=True,
        )
        return bool(result)

    async def get_user_profile(self, user_id: int) -> UserProfileRecord | None:
        cached = self._get_local(user_profile_key(user_id))
        if cached is not None:
            profile = cached
            profile.has_active_quiz = await self.has_active_quiz(user_id)
            return profile

        payload = await self.redis_client.get(user_profile_key(user_id))
        if not payload:
            return None

        await self._refresh_expiry(user_profile_key(user_id), USER_PROFILE_TTL_SECONDS)
        data = json.loads(payload)
        record = UserProfileRecord.from_dict(data)
        self._set_local(user_profile_key(user_id), record, USER_PROFILE_TTL_SECONDS)
        record.has_active_quiz = await self.has_active_quiz(user_id)
        return record

    async def set_user_profile(self, profile: UserProfileRecord) -> None:
        await self.redis_client.set(
            user_profile_key(profile.id),
            json.dumps(profile.to_dict()),
            ex=USER_PROFILE_TTL_SECONDS,
        )
        self._set_local(user_profile_key(profile.id), profile, USER_PROFILE_TTL_SECONDS)

    async def invalidate_user_profile(self, user_id: int) -> None:
        await self._delete_key(user_profile_key(user_id))
        self._local_cache.pop(user_profile_key(user_id), None)

    async def get_active_quiz(self, user_id: int) -> str | None:
        cached = self._get_local(active_quiz_key(user_id))
        if cached is not None:
            return cached

        session_id = await self.redis_client.get(active_quiz_key(user_id))
        if session_id:
            await self._refresh_expiry(active_quiz_key(user_id), ACTIVE_QUIZ_TTL_SECONDS)
            self._set_local(
                active_quiz_key(user_id),
                session_id,
                ACTIVE_QUIZ_TTL_SECONDS,
            )
        return session_id

    async def set_active_quiz(self, user_id: int, session_id: str) -> None:
        await self.redis_client.set(
            active_quiz_key(user_id),
            session_id,
            ex=ACTIVE_QUIZ_TTL_SECONDS,
        )
        self._set_local(active_quiz_key(user_id), session_id, ACTIVE_QUIZ_TTL_SECONDS)

    async def clear_active_quiz(self, user_id: int) -> None:
        await self._delete_key(active_quiz_key(user_id))
        self._local_cache.pop(active_quiz_key(user_id), None)

    async def has_active_quiz(self, user_id: int) -> bool:
        return bool(await self.get_active_quiz(user_id))

    async def get_quiz_session(self, session_id: str) -> QuizSessionState | None:
        payload = await self.redis_client.get(quiz_session_key(session_id))
        if not payload:
            return None

        await self._refresh_expiry(quiz_session_key(session_id), QUIZ_SESSION_TTL_SECONDS)
        return QuizSessionState.from_dict(json.loads(payload))

    async def set_quiz_session(self, session: QuizSessionState) -> None:
        await self.redis_client.set(
            quiz_session_key(session.session_id),
            json.dumps(session.to_dict()),
            ex=QUIZ_SESSION_TTL_SECONDS,
        )

    async def set_poll_map(self, poll_map: PollMapRecord) -> None:
        await self.redis_client.set(
            poll_map_key(poll_map.poll_id),
            json.dumps(poll_map.to_dict()),
            ex=POLL_MAP_TTL_SECONDS,
        )

    async def get_poll_map(self, poll_id: str) -> PollMapRecord | None:
        payload = await self.redis_client.get(poll_map_key(poll_id))
        if not payload:
            return None

        await self._refresh_expiry(poll_map_key(poll_id), POLL_MAP_TTL_SECONDS)
        return PollMapRecord.from_dict(json.loads(payload))

    async def cache_question_bank(
        self, course_id: str, questions: list[QuizQuestion], ttl_seconds: int = 3600
    ) -> None:
        await self.redis_client.set(
            question_bank_cache_key(course_id),
            json.dumps([question.to_dict() for question in questions]),
            ex=ttl_seconds,
        )

    async def get_question_bank(self, course_id: str) -> list[QuizQuestion] | None:
        cached = self._get_local(question_bank_cache_key(course_id))
        if cached is not None:
            return cached

        payload = await self.redis_client.get(question_bank_cache_key(course_id))
        if not payload:
            return None
        questions = [QuizQuestion.from_dict(item) for item in json.loads(payload)]
        self._set_local(question_bank_cache_key(course_id), questions, 3600)
        return questions

    async def get_adaptive_snapshot(self, user_id: int, course_id: str) -> dict | None:
        key = adaptive_snapshot_key(user_id, course_id)
        cached = self._get_local(key)
        if cached is not None:
            return cached

        payload = await self.redis_client.get(key)
        if not payload:
            return None
        await self._refresh_expiry(key, ADAPTIVE_SNAPSHOT_TTL_SECONDS)
        snapshot = json.loads(payload)
        self._set_local(key, snapshot, ADAPTIVE_SNAPSHOT_TTL_SECONDS)
        return snapshot

    async def set_adaptive_snapshot(
        self,
        user_id: int,
        course_id: str,
        snapshot: dict,
        ttl_seconds: int = ADAPTIVE_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        key = adaptive_snapshot_key(user_id, course_id)
        await self.redis_client.set(
            key,
            json.dumps(snapshot),
            ex=ttl_seconds,
        )
        self._set_local(key, snapshot, ttl_seconds)

    async def invalidate_adaptive_snapshot(self, user_id: int, course_id: str) -> None:
        key = adaptive_snapshot_key(user_id, course_id)
        await self._delete_key(key)
        self._local_cache.pop(key, None)

    async def cache_catalog_faculties(
        self, faculties: list[dict], ttl_seconds: int = CATALOG_LOOKUP_TTL_SECONDS
    ) -> None:
        await self._cache_catalog_value("faculties", faculties, ttl_seconds)

    async def get_catalog_faculties(self) -> list[dict] | None:
        return await self._get_catalog_value("faculties")

    async def invalidate_catalog_faculties(self) -> None:
        await self._invalidate_catalog_value("faculties")

    async def cache_catalog_programs(
        self,
        faculty_code: str,
        programs: list[dict],
        ttl_seconds: int = CATALOG_LOOKUP_TTL_SECONDS,
    ) -> None:
        await self._cache_catalog_value("programs", programs, ttl_seconds, faculty_code)

    async def get_catalog_programs(self, faculty_code: str) -> list[dict] | None:
        return await self._get_catalog_value("programs", faculty_code)

    async def invalidate_catalog_programs(self, faculty_code: str) -> None:
        await self._invalidate_catalog_value("programs", faculty_code)

    async def cache_catalog_levels(
        self,
        program_code: str,
        levels: list[dict],
        ttl_seconds: int = CATALOG_LOOKUP_TTL_SECONDS,
    ) -> None:
        await self._cache_catalog_value("levels", levels, ttl_seconds, program_code)

    async def get_catalog_levels(self, program_code: str) -> list[dict] | None:
        return await self._get_catalog_value("levels", program_code)

    async def invalidate_catalog_levels(self, program_code: str) -> None:
        await self._invalidate_catalog_value("levels", program_code)

    async def cache_catalog_semesters(
        self,
        program_code: str,
        level_code: str,
        semesters: list[dict],
        ttl_seconds: int = CATALOG_LOOKUP_TTL_SECONDS,
    ) -> None:
        await self._cache_catalog_value(
            "semesters",
            semesters,
            ttl_seconds,
            program_code,
            level_code,
        )

    async def get_catalog_semesters(
        self, program_code: str, level_code: str
    ) -> list[dict] | None:
        return await self._get_catalog_value("semesters", program_code, level_code)

    async def invalidate_catalog_semesters(self, program_code: str, level_code: str) -> None:
        await self._invalidate_catalog_value("semesters", program_code, level_code)

    async def cache_catalog_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
        courses: list[dict],
        ttl_seconds: int = CATALOG_LOOKUP_TTL_SECONDS,
    ) -> None:
        await self._cache_catalog_value(
            "courses",
            courses,
            ttl_seconds,
            faculty_code,
            program_code,
            level_code,
            semester_code,
        )

    async def get_catalog_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ) -> list[dict] | None:
        return await self._get_catalog_value(
            "courses",
            faculty_code,
            program_code,
            level_code,
            semester_code,
        )

    async def invalidate_catalog_courses(
        self,
        faculty_code: str,
        program_code: str,
        level_code: str,
        semester_code: str,
    ) -> None:
        await self._invalidate_catalog_value(
            "courses",
            faculty_code,
            program_code,
            level_code,
            semester_code,
        )

    async def invalidate_catalog_cache(self) -> None:
        for key in list(self._catalog_cache_keys):
            await self._delete_key(key)
            self._local_cache.pop(key, None)
            self._catalog_cache_keys.discard(key)

    async def claim_analytics_event(
        self, user_id: int, event_type: str, ttl_seconds: int = 24 * 60 * 60
    ) -> bool:
        result = await self.redis_client.set(
            analytics_dedupe_key(user_id, event_type),
            "1",
            ex=ttl_seconds,
            nx=True,
        )
        return bool(result)

    async def acquire_quiz_lock(self, session_id: str) -> str | None:
        token = str(uuid.uuid4())
        acquired = await self.redis_client.set(
            quiz_session_lock_key(session_id),
            token,
            ex=LOCK_TTL_SECONDS,
            nx=True,
        )
        if not acquired:
            return None
        return token

    async def acquire_adaptive_update_lock(self, user_id: int, course_id: str) -> str | None:
        token = str(uuid.uuid4())
        acquired = await self.redis_client.set(
            adaptive_update_lock_key(user_id, course_id),
            token,
            ex=LOCK_TTL_SECONDS,
            nx=True,
        )
        if not acquired:
            return None
        return token

    async def release_adaptive_update_lock(
        self, user_id: int, course_id: str, token: str
    ) -> None:
        key = adaptive_update_lock_key(user_id, course_id)
        current_token = await self.redis_client.get(key)
        if current_token != token:
            return
        await self._delete_key(key)

    async def release_quiz_lock(self, session_id: str, token: str) -> None:
        key = quiz_session_lock_key(session_id)
        current_token = await self.redis_client.get(key)
        if current_token != token:
            return
        await self._delete_key(key)

    async def _delete_key(self, key: str) -> None:
        delete_method = getattr(self.redis_client, "delete", None)
        if delete_method is not None:
            await delete_method(key)

    async def _refresh_expiry(self, key: str, seconds: int) -> None:
        expire_method = getattr(self.redis_client, "expire", None)
        if expire_method is not None:
            await expire_method(key, seconds)

    def _get_local(self, key: str):
        item = self._local_cache.get(key)
        if item is None:
            return None

        expires_at, value = item
        if expires_at < time.monotonic():
            self._local_cache.pop(key, None)
            return None
        return value

    def _set_local(self, key: str, value, ttl_seconds: int) -> None:
        self._local_cache[key] = (time.monotonic() + ttl_seconds, value)

    def _catalog_key(self, scope: str, *parts: str) -> str:
        suffix = ":".join(parts)
        return f"catalog:{scope}" if not suffix else f"catalog:{scope}:{suffix}"

    async def _cache_catalog_value(
        self,
        scope: str,
        value,
        ttl_seconds: int,
        *parts: str,
    ) -> None:
        key = self._catalog_key(scope, *parts)
        await self.redis_client.set(
            key,
            json.dumps(value),
            ex=ttl_seconds,
        )
        self._set_local(key, value, ttl_seconds)
        self._catalog_cache_keys.add(key)

    async def _get_catalog_value(self, scope: str, *parts: str):
        key = self._catalog_key(scope, *parts)
        cached = self._get_local(key)
        if cached is not None:
            return cached

        payload = await self.redis_client.get(key)
        if not payload:
            return None

        await self._refresh_expiry(key, CATALOG_LOOKUP_TTL_SECONDS)
        value = json.loads(payload)
        self._set_local(key, value, CATALOG_LOOKUP_TTL_SECONDS)
        self._catalog_cache_keys.add(key)
        return value

    async def _invalidate_catalog_value(self, scope: str, *parts: str) -> None:
        key = self._catalog_key(scope, *parts)
        await self._delete_key(key)
        self._local_cache.pop(key, None)
        self._catalog_cache_keys.discard(key)
