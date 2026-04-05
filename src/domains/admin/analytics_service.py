from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from src.cache import redis_client
from src.infra.db.models.catalog_course import CatalogCourse
from src.infra.db.models.catalog_faculty import CatalogFaculty
from src.infra.db.models.catalog_program import CatalogProgram
from src.infra.db.models.question_attempt import QuestionAttempt
from src.infra.db.models.question_report import QuestionReport
from src.infra.db.models.student_course_state import StudentCourseState
from src.infra.db.models.student_question_srs import StudentQuestionSrs
from src.infra.db.models.telegram_identity import TelegramIdentity
from src.infra.db.models.user_bot_profile import UserBotProfile
from src.infra.db.models.user import User
from src.infra.redis.admin_cache_store import AdminCacheStore
from src.infra.db.session import AsyncSessionLocal


ANALYTICS_SUMMARY_CACHE_TTL_SECONDS = 300
ANALYTICS_SUMMARY_WINDOW_DAYS = 30
ANALYTICS_STUDENT_CACHE_TTL_SECONDS = 90


class AdminAnalyticsService:
    def __init__(
        self,
        session_factory=AsyncSessionLocal,
        cache_store: AdminCacheStore | None = None,
    ):
        self.session_factory = session_factory
        self.cache_store = cache_store or AdminCacheStore(redis_client)

    async def get_summary(
        self,
        *,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
    ) -> dict:
        """Return analytics summary from cache. Falls back to empty data if cache is cold."""
        cached = await self.cache_store.get_json(
            "analytics-summary",
            bot_id=active_bot_id,
            course_codes=course_codes,
        )
        if cached is not None:
            return cached

        # Cache miss — compute synchronously but with a time window cap
        return await self.precompute_summary(
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )

    async def precompute_summary(
        self,
        *,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
    ) -> dict:
        """Compute analytics summary from database and write to cache.

        Safe to call from a background worker on a schedule.
        """
        since = datetime.now(UTC) - timedelta(days=ANALYTICS_SUMMARY_WINDOW_DAYS)
        attempts = await self._list_attempts(
            active_bot_id=active_bot_id,
            course_codes=course_codes,
            since=since,
        )
        course_names = await self._load_course_names({attempt.course_id for attempt in attempts})
        leaderboard = await self._build_leaderboard(
            attempts,
            course_names,
            active_bot_id=active_bot_id,
        )
        payload = {
            "kpis": self._build_kpis(attempts, leaderboard),
            "daily_usage": self._build_daily_usage(attempts, days=7),
            "leaderboard": leaderboard,
        }
        await self.cache_store.set_json(
            "analytics-summary",
            payload,
            bot_id=active_bot_id,
            course_codes=course_codes,
            ttl_seconds=ANALYTICS_SUMMARY_CACHE_TTL_SECONDS,
        )
        return payload

    async def get_student_detail(
        self,
        user_id: int,
        *,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
    ) -> dict | None:
        cached = await self.cache_store.get_json(
            "analytics-student",
            bot_id=active_bot_id,
            course_codes=course_codes,
            extra_parts=(user_id,),
        )
        if cached is not None:
            return cached

        user = await self._get_user(user_id)
        user_profile = await self._get_user_profile(user_id, active_bot_id=active_bot_id)
        attempts = await self._list_attempts(
            user_id=user_id,
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )
        course_states = await self._list_student_course_states(
            user_id=user_id,
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )
        reports = await self._list_question_reports(
            user_id=user_id,
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )

        if user is None and not attempts and not course_states and not reports:
            return None

        identity = await self._get_telegram_identity(user_id)
        course_ids = {
            attempt.course_id for attempt in attempts
        } | {state.course_id for state in course_states}
        course_names = await self._load_course_names(course_ids)
        faculty_name = await self._load_faculty_name(
            getattr(user_profile, "faculty_code", None)
        )
        program_name = await self._load_program_name(
            getattr(user_profile, "program_code", None)
        )

        attempts_by_course: dict[str, list[QuestionAttempt]] = defaultdict(list)
        for attempt in attempts:
            attempts_by_course[attempt.course_id].append(attempt)

        states_by_course = {state.course_id: state for state in course_states}
        streak_current, streak_longest = self._streak_stats(
            {self._as_date(attempt.created_at) for attempt in attempts}
        )
        total_correct = sum(1 for attempt in attempts if attempt.is_correct)
        total_quizzes_completed = sum(
            int(getattr(state, "total_quizzes_completed", 0) or 0) for state in course_states
        )
        last_active_at = self._resolve_last_active_at(
            attempts=attempts,
            reports=reports,
            user=user,
        )

        profile = {
            "user_id": str(user_id),
            "display_name": getattr(user, "display_name", None)
            or getattr(identity, "username", None)
            or f"Student {user_id}",
            "telegram_user_id": str(getattr(identity, "telegram_user_id", user_id)),
            "telegram_username": getattr(identity, "username", None) or f"user_{user_id}",
            "faculty_code": getattr(user_profile, "faculty_code", None) or "",
            "faculty_name": faculty_name,
            "program_code": getattr(user_profile, "program_code", None) or "",
            "program_name": program_name,
            "level_code": getattr(user_profile, "level_code", None) or "",
            "semester_code": getattr(user_profile, "semester_code", None) or "",
            "preferred_course_code": getattr(user_profile, "preferred_course_code", None) or "",
            "onboarding_completed": bool(
                getattr(user_profile, "onboarding_completed", False)
            ),
            "created_at": self._isoformat(
                getattr(user_profile, "created_at", None)
                or getattr(user, "created_at", None)
                or last_active_at
                or datetime.now(UTC)
            ),
            "last_active_at": self._isoformat(last_active_at or datetime.now(UTC)),
            "current_streak": streak_current,
            "longest_streak": streak_longest,
            "total_questions_answered": len(attempts),
            "total_correct": total_correct,
            "total_quizzes_completed": total_quizzes_completed,
            "reports_filed": len(reports),
        }

        courses = []
        ordered_course_ids = sorted(
            course_ids,
            key=lambda course_id: (
                -len(attempts_by_course.get(course_id, [])),
                course_names.get(course_id, course_id),
            ),
        )
        for course_id in ordered_course_ids:
            course_attempts = attempts_by_course.get(course_id, [])
            state = states_by_course.get(course_id)
            total_attempts = len(course_attempts)
            total_course_correct = sum(1 for attempt in course_attempts if attempt.is_correct)
            timed_attempts = [
                float(attempt.time_taken_seconds)
                for attempt in course_attempts
                if attempt.time_taken_seconds is not None
            ]
            avg_time = (
                round(sum(timed_attempts) / len(timed_attempts), 1) if timed_attempts else 0.0
            )
            overall_skill = (
                float(getattr(state, "overall_skill", 0) or 0)
                if state is not None
                else self._skill_from_accuracy(total_course_correct, total_attempts)
            )
            courses.append(
                {
                    "course_id": course_id,
                    "course_name": course_names.get(course_id, self._humanize_code(course_id)),
                    "overall_skill": round(overall_skill, 2),
                    "phase": getattr(state, "phase", None)
                    or self._phase_from_skill(overall_skill),
                    "topic_skills": dict(getattr(state, "topic_skills", {}) or {}),
                    "cognitive_profile": dict(getattr(state, "cognitive_profile", {}) or {}),
                    "processing_profile": dict(getattr(state, "processing_profile", {}) or {}),
                    "misconception_flags": list(
                        getattr(state, "misconception_flags", []) or []
                    ),
                    "total_quizzes_completed": int(
                        getattr(state, "total_quizzes_completed", 0) or 0
                    ),
                    "total_attempts": total_attempts,
                    "total_correct": total_course_correct,
                    "avg_time_per_question": avg_time,
                    "exam_date": self._isoformat(getattr(state, "exam_date", None)),
                }
            )

        leaderboard_entry = await self._find_leaderboard_entry(
            user_id=user_id,
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )

        payload = {
            "profile": profile,
            "courses": courses,
            "srs": await self._build_srs_distribution(
                user_id=user_id,
                active_bot_id=active_bot_id,
                course_codes=course_codes,
                course_names=course_names,
            ),
            "weekly_progress": self._build_weekly_progress(attempts, weeks=12),
            "daily_activity": self._build_daily_activity(attempts, days=30),
            "recent_attempts": self._build_recent_attempts(
                attempts=attempts,
                course_names=course_names,
                limit=20,
            ),
            "leaderboard_entry": leaderboard_entry,
        }
        await self.cache_store.set_json(
            "analytics-student",
            payload,
            bot_id=active_bot_id,
            course_codes=course_codes,
            extra_parts=(user_id,),
            ttl_seconds=ANALYTICS_STUDENT_CACHE_TTL_SECONDS,
        )
        return payload

    async def _build_leaderboard(
        self,
        attempts: list[QuestionAttempt],
        course_names: dict[str, str],
        *,
        active_bot_id: str | None = None,
    ) -> list[dict]:
        attempts_by_user: dict[int, list[QuestionAttempt]] = defaultdict(list)
        for attempt in attempts:
            attempts_by_user[attempt.user_id].append(attempt)

        if not attempts_by_user:
            return []

        user_ids = set(attempts_by_user)
        users = await self._load_users(user_ids)
        user_profiles = await self._load_user_profiles(user_ids, active_bot_id=active_bot_id)
        identities = await self._load_telegram_identities(user_ids)
        course_states = await self._load_student_course_states_for_users(
            user_ids,
            active_bot_id=active_bot_id,
            course_codes=set(course_names) if course_names else None,
        )

        entries = []
        for user_id, user_attempts in attempts_by_user.items():
            correct_count = sum(1 for attempt in user_attempts if attempt.is_correct)
            course_buckets: dict[str, list[QuestionAttempt]] = defaultdict(list)
            for attempt in user_attempts:
                course_buckets[attempt.course_id].append(attempt)

            top_course_id = max(
                course_buckets,
                key=lambda course_id: (
                    len(course_buckets[course_id]),
                    sum(1 for attempt in course_buckets[course_id] if attempt.is_correct),
                ),
            )
            state_rows = course_states.get(user_id, [])
            if state_rows:
                overall_skill = round(
                    sum(float(getattr(row, "overall_skill", 0) or 0) for row in state_rows)
                    / len(state_rows),
                    2,
                )
                phase = self._dominant_phase(state_rows)
            else:
                overall_skill = round(
                    self._skill_from_accuracy(correct_count, len(user_attempts)),
                    2,
                )
                phase = self._phase_from_skill(overall_skill)

            streak_current, _ = self._streak_stats(
                {self._as_date(attempt.created_at) for attempt in user_attempts}
            )
            identity = identities.get(user_id)
            user = users.get(user_id)
            user_profile = user_profiles.get(user_id)
            accuracy = self._accuracy_percent(correct_count, len(user_attempts))
            entries.append(
                {
                    "user_id": str(user_id),
                    "telegram_username": getattr(identity, "username", None)
                    or getattr(user, "display_name", None)
                    or f"user_{user_id}",
                    "telegram_id": str(getattr(identity, "telegram_user_id", user_id)),
                    "questions_answered": len(user_attempts),
                    "daily_streak": streak_current,
                    "accuracy": accuracy,
                    "overall_skill": overall_skill,
                    "phase": phase,
                    "top_course": course_names.get(
                        top_course_id,
                        self._humanize_code(top_course_id),
                    ),
                }
            )

        entries.sort(
            key=lambda entry: (
                -entry["questions_answered"],
                -entry["accuracy"],
                -entry["overall_skill"],
                entry["telegram_username"],
            )
        )
        for index, entry in enumerate(entries, start=1):
            entry["rank"] = index
        return entries[:50]

    async def _find_leaderboard_entry(
        self,
        *,
        user_id: int,
        active_bot_id: str | None,
        course_codes: set[str] | None,
    ) -> dict | None:
        attempts = await self._list_attempts(
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )
        course_names = await self._load_course_names({attempt.course_id for attempt in attempts})
        leaderboard = await self._build_leaderboard(
            attempts,
            course_names,
            active_bot_id=active_bot_id,
        )
        for entry in leaderboard:
            if entry["user_id"] == str(user_id):
                return entry
        return None

    def _build_kpis(self, attempts: list[QuestionAttempt], leaderboard: list[dict]) -> list[dict]:
        today = datetime.now(UTC).date()
        current_start = today - timedelta(days=6)
        previous_start = current_start - timedelta(days=7)
        previous_end = current_start - timedelta(days=1)

        current_attempts = [
            attempt
            for attempt in attempts
            if current_start <= self._as_date(attempt.created_at) <= today
        ]
        previous_attempts = [
            attempt
            for attempt in attempts
            if previous_start <= self._as_date(attempt.created_at) <= previous_end
        ]

        current_active_users = len({attempt.user_id for attempt in current_attempts})
        previous_active_users = len({attempt.user_id for attempt in previous_attempts})

        current_question_count = len(current_attempts)
        previous_question_count = len(previous_attempts)

        current_accuracy = self._accuracy_percent(
            sum(1 for attempt in current_attempts if attempt.is_correct),
            len(current_attempts),
        )
        previous_accuracy = self._accuracy_percent(
            sum(1 for attempt in previous_attempts if attempt.is_correct),
            len(previous_attempts),
        )

        current_active_days = (
            round(
                sum(
                    len(
                        {
                            self._as_date(attempt.created_at)
                            for attempt in attempts
                            if attempt.user_id == int(entry["user_id"])
                            and current_start <= self._as_date(attempt.created_at) <= today
                        }
                    )
                    for entry in leaderboard
                )
                / len(leaderboard),
                1,
            )
            if leaderboard
            else 0.0
        )
        previous_active_days = (
            round(
                sum(
                    len(
                        {
                            self._as_date(attempt.created_at)
                            for attempt in attempts
                            if attempt.user_id == int(entry["user_id"])
                            and previous_start
                            <= self._as_date(attempt.created_at)
                            <= previous_end
                        }
                    )
                    for entry in leaderboard
                )
                / len(leaderboard),
                1,
            )
            if leaderboard
            else 0.0
        )

        return [
            {
                "label": "Active Users (7d)",
                "value": f"{current_active_users:,}",
                "change": self._relative_change(current_active_users, previous_active_users),
                "trend": self._trend(current_active_users, previous_active_users),
            },
            {
                "label": "Questions Answered (7d)",
                "value": f"{current_question_count:,}",
                "change": self._relative_change(current_question_count, previous_question_count),
                "trend": self._trend(current_question_count, previous_question_count),
            },
            {
                "label": "Accuracy (7d)",
                "value": f"{current_accuracy:.1f}%",
                "change": self._delta_change(current_accuracy, previous_accuracy, suffix="pp"),
                "trend": self._trend(current_accuracy, previous_accuracy),
            },
            {
                "label": "Avg. Active Days/User",
                "value": f"{current_active_days:.1f}",
                "change": self._delta_change(current_active_days, previous_active_days),
                "trend": self._trend(current_active_days, previous_active_days),
            },
        ]

    def _build_daily_usage(self, attempts: list[QuestionAttempt], *, days: int) -> list[dict]:
        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)
        by_day_users: dict[date, set[int]] = defaultdict(set)
        by_day_questions: dict[date, int] = defaultdict(int)
        for attempt in attempts:
            day = self._as_date(attempt.created_at)
            if start <= day <= today:
                by_day_users[day].add(attempt.user_id)
                by_day_questions[day] += 1

        payload = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            payload.append(
                {
                    "date": day.strftime("%a"),
                    "users": len(by_day_users.get(day, set())),
                    "questions": by_day_questions.get(day, 0),
                }
            )
        return payload

    def _build_weekly_progress(self, attempts: list[QuestionAttempt], *, weeks: int) -> list[dict]:
        today = datetime.now(UTC).date()
        start_of_week = today - timedelta(days=today.weekday())
        week_starts = [
            start_of_week - timedelta(weeks=index) for index in range(weeks - 1, -1, -1)
        ]

        buckets: dict[date, list[QuestionAttempt]] = defaultdict(list)
        for attempt in attempts:
            day = self._as_date(attempt.created_at)
            week_start = day - timedelta(days=day.weekday())
            if week_start >= week_starts[0]:
                buckets[week_start].append(attempt)

        payload = []
        for week_start in week_starts:
            week_attempts = buckets.get(week_start, [])
            timed_attempts = [
                float(attempt.time_taken_seconds)
                for attempt in week_attempts
                if attempt.time_taken_seconds is not None
            ]
            correct_count = sum(1 for attempt in week_attempts if attempt.is_correct)
            payload.append(
                {
                    "week": week_start.strftime("%b %d"),
                    "attempts": len(week_attempts),
                    "correct": correct_count,
                    "accuracy": self._accuracy_percent(correct_count, len(week_attempts)),
                    "avg_time": round(sum(timed_attempts) / len(timed_attempts), 1)
                    if timed_attempts
                    else 0.0,
                }
            )
        return payload

    def _build_daily_activity(self, attempts: list[QuestionAttempt], *, days: int) -> list[dict]:
        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)
        counts: dict[date, int] = defaultdict(int)
        for attempt in attempts:
            day = self._as_date(attempt.created_at)
            if start <= day <= today:
                counts[day] += 1

        return [
            {
                "date": (start + timedelta(days=offset)).isoformat(),
                "questions_count": counts.get(start + timedelta(days=offset), 0),
            }
            for offset in range(days)
        ]

    def _build_recent_attempts(
        self,
        *,
        attempts: list[QuestionAttempt],
        course_names: dict[str, str],
        limit: int,
    ) -> list[dict]:
        payload = []
        for attempt in sorted(
            attempts,
            key=lambda item: (item.created_at, item.id),
            reverse=True,
        )[:limit]:
            payload.append(
                {
                    "question_key": attempt.question_key,
                    "course_name": course_names.get(
                        attempt.course_id,
                        self._humanize_code(attempt.course_id),
                    ),
                    "is_correct": bool(attempt.is_correct),
                    "time_taken_seconds": float(attempt.time_taken_seconds or 0),
                    "created_at": self._isoformat(attempt.created_at),
                }
            )
        return payload

    async def _build_srs_distribution(
        self,
        *,
        user_id: int,
        active_bot_id: str | None,
        course_codes: set[str] | None,
        course_names: dict[str, str],
    ) -> list[dict]:
        records = await self._list_srs_records(
            user_id=user_id,
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )
        buckets: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        for record in records:
            buckets[record.course_id][int(record.box)] += 1

        payload = []
        for course_id in sorted(buckets, key=lambda code: course_names.get(code, code)):
            box_counts = buckets[course_id]
            payload.append(
                {
                    "course_id": course_id,
                    "course_name": course_names.get(course_id, self._humanize_code(course_id)),
                    "box_0": box_counts.get(0, 0),
                    "box_1": box_counts.get(1, 0),
                    "box_2": box_counts.get(2, 0),
                    "box_3": box_counts.get(3, 0),
                    "box_4": box_counts.get(4, 0),
                    "box_5": box_counts.get(5, 0),
                }
            )
        return payload

    async def _get_user(self, user_id: int) -> User | None:
        async with self.session_factory() as session:
            return await session.get(User, user_id)

    async def _get_user_profile(
        self,
        user_id: int,
        *,
        active_bot_id: str | None,
    ) -> UserBotProfile | None:
        if active_bot_id is None:
            return None

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserBotProfile).where(
                    UserBotProfile.user_id == user_id,
                    UserBotProfile.bot_id == active_bot_id,
                )
            )
            return result.scalar_one_or_none()

    async def _get_telegram_identity(self, user_id: int) -> TelegramIdentity | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(TelegramIdentity).where(TelegramIdentity.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def _list_attempts(
        self,
        *,
        user_id: int | None = None,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[QuestionAttempt]:
        if course_codes is not None and not course_codes:
            return []

        async with self.session_factory() as session:
            stmt = select(QuestionAttempt)
            if user_id is not None:
                stmt = stmt.where(QuestionAttempt.user_id == user_id)
            if active_bot_id is not None:
                stmt = stmt.where(QuestionAttempt.bot_id == active_bot_id)
            if course_codes is not None:
                stmt = stmt.where(QuestionAttempt.course_id.in_(sorted(course_codes)))
            if since is not None:
                stmt = stmt.where(QuestionAttempt.created_at >= since)
            stmt = stmt.order_by(QuestionAttempt.created_at.desc(), QuestionAttempt.id.desc())
            if limit is not None:
                stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _list_student_course_states(
        self,
        *,
        user_id: int,
        active_bot_id: str | None,
        course_codes: set[str] | None,
    ) -> list[StudentCourseState]:
        if course_codes is not None and not course_codes:
            return []

        async with self.session_factory() as session:
            stmt = select(StudentCourseState).where(StudentCourseState.user_id == user_id)
            if active_bot_id is not None:
                stmt = stmt.where(StudentCourseState.bot_id == active_bot_id)
            if course_codes is not None:
                stmt = stmt.where(StudentCourseState.course_id.in_(sorted(course_codes)))
            stmt = stmt.order_by(StudentCourseState.course_id.asc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _load_student_course_states_for_users(
        self,
        user_ids: set[int],
        *,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
    ) -> dict[int, list[StudentCourseState]]:
        if not user_ids:
            return {}
        if course_codes is not None and not course_codes:
            return {}

        async with self.session_factory() as session:
            stmt = select(StudentCourseState).where(StudentCourseState.user_id.in_(sorted(user_ids)))
            if active_bot_id is not None:
                stmt = stmt.where(StudentCourseState.bot_id == active_bot_id)
            if course_codes is not None:
                stmt = stmt.where(StudentCourseState.course_id.in_(sorted(course_codes)))
            result = await session.execute(stmt)
            rows = list(result.scalars().all())

        payload: dict[int, list[StudentCourseState]] = defaultdict(list)
        for row in rows:
            payload[row.user_id].append(row)
        return payload

    async def _list_srs_records(
        self,
        *,
        user_id: int,
        active_bot_id: str | None,
        course_codes: set[str] | None,
    ) -> list[StudentQuestionSrs]:
        if course_codes is not None and not course_codes:
            return []

        async with self.session_factory() as session:
            stmt = select(StudentQuestionSrs).where(StudentQuestionSrs.user_id == user_id)
            if active_bot_id is not None:
                stmt = stmt.where(StudentQuestionSrs.bot_id == active_bot_id)
            if course_codes is not None:
                stmt = stmt.where(StudentQuestionSrs.course_id.in_(sorted(course_codes)))
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _list_question_reports(
        self,
        *,
        user_id: int,
        active_bot_id: str | None,
        course_codes: set[str] | None,
    ) -> list[QuestionReport]:
        if course_codes is not None and not course_codes:
            return []

        async with self.session_factory() as session:
            stmt = select(QuestionReport).where(QuestionReport.user_id == user_id)
            if active_bot_id is not None:
                stmt = stmt.where(QuestionReport.bot_id == active_bot_id)
            if course_codes is not None:
                stmt = stmt.where(QuestionReport.course_id.in_(sorted(course_codes)))
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _load_course_names(self, course_ids: set[str]) -> dict[str, str]:
        if not course_ids:
            return {}

        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogCourse).where(CatalogCourse.code.in_(sorted(course_ids)))
            )
            return {course.code: course.name for course in result.scalars().all()}

    async def _load_users(self, user_ids: set[int]) -> dict[int, User]:
        if not user_ids:
            return {}

        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id.in_(sorted(user_ids))))
            return {user.id: user for user in result.scalars().all()}

    async def _load_user_profiles(
        self,
        user_ids: set[int],
        *,
        active_bot_id: str | None,
    ) -> dict[int, UserBotProfile]:
        if not user_ids or active_bot_id is None:
            return {}

        async with self.session_factory() as session:
            result = await session.execute(
                select(UserBotProfile).where(
                    UserBotProfile.user_id.in_(sorted(user_ids)),
                    UserBotProfile.bot_id == active_bot_id,
                )
            )
            return {profile.user_id: profile for profile in result.scalars().all()}

    async def _load_telegram_identities(self, user_ids: set[int]) -> dict[int, TelegramIdentity]:
        if not user_ids:
            return {}

        async with self.session_factory() as session:
            result = await session.execute(
                select(TelegramIdentity).where(TelegramIdentity.user_id.in_(sorted(user_ids)))
            )
            return {identity.user_id: identity for identity in result.scalars().all()}

    async def _load_faculty_name(self, faculty_code: str | None) -> str:
        if not faculty_code:
            return ""

        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogFaculty).where(CatalogFaculty.code == faculty_code)
            )
            faculty = result.scalar_one_or_none()
            return faculty.name if faculty is not None else self._humanize_code(faculty_code)

    async def _load_program_name(self, program_code: str | None) -> str:
        if not program_code:
            return ""

        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogProgram).where(CatalogProgram.code == program_code)
            )
            program = result.scalar_one_or_none()
            return program.name if program is not None else self._humanize_code(program_code)

    def _resolve_last_active_at(
        self,
        *,
        attempts: list[QuestionAttempt],
        reports: list[QuestionReport],
        user: User | None,
    ) -> datetime | None:
        candidates = [attempt.created_at for attempt in attempts]
        candidates.extend(report.created_at for report in reports)
        if user is not None and getattr(user, "created_at", None) is not None:
            candidates.append(user.created_at)
        if not candidates:
            return None
        return max(candidates)

    def _streak_stats(self, active_days: set[date]) -> tuple[int, int]:
        if not active_days:
            return 0, 0

        ordered_days = sorted(active_days)
        longest = 0
        running = 0
        previous_day: date | None = None
        for day in ordered_days:
            if previous_day is not None and day == previous_day + timedelta(days=1):
                running += 1
            else:
                running = 1
            previous_day = day
            longest = max(longest, running)

        current = 0
        cursor = ordered_days[-1]
        while cursor in active_days:
            current += 1
            cursor -= timedelta(days=1)
        return current, longest

    def _accuracy_percent(self, correct_count: int, total_count: int) -> float:
        if total_count <= 0:
            return 0.0
        return round((correct_count / total_count) * 100, 1)

    def _skill_from_accuracy(self, correct_count: int, total_count: int) -> float:
        if total_count <= 0:
            return 0.0
        return max(0.5, min(5.0, round((correct_count / total_count) * 5, 2)))

    def _phase_from_skill(self, overall_skill: float) -> str:
        if overall_skill >= 3.5:
            return "established"
        if overall_skill >= 2.0:
            return "warm"
        return "cold_start"

    def _dominant_phase(self, course_states: list[StudentCourseState]) -> str:
        if not course_states:
            return "cold_start"

        ranking = {"cold_start": 0, "warm": 1, "established": 2}
        return max(
            (
                str(getattr(state, "phase", "cold_start") or "cold_start")
                for state in course_states
            ),
            key=lambda phase: ranking.get(phase, 0),
        )

    def _relative_change(self, current_value: int, previous_value: int) -> str:
        if previous_value <= 0:
            if current_value <= 0:
                return "0%"
            return "+100%"

        delta = ((current_value - previous_value) / previous_value) * 100
        return f"{delta:+.1f}%"

    def _delta_change(
        self,
        current_value: float,
        previous_value: float,
        *,
        suffix: str = "",
    ) -> str:
        delta = current_value - previous_value
        return f"{delta:+.1f}{suffix}"

    def _trend(self, current_value: float, previous_value: float) -> str:
        if current_value > previous_value:
            return "up"
        if current_value < previous_value:
            return "down"
        return "flat"

    def _humanize_code(self, value: str | None) -> str:
        if not value:
            return ""
        return str(value).replace("-", " ").replace("_", " ").title()

    def _as_date(self, value: datetime) -> date:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).date()

    def _isoformat(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
