from __future__ import annotations

from src.cache import redis_client
from src.infra.db.models.catalog_course import CatalogCourse
from src.infra.db.repositories.audit_log_repository import AuditLogRepository
from src.infra.db.repositories.question_bank_repository import QuestionBankRepository
from src.infra.db.session import AsyncSessionLocal
from src.infra.redis.admin_cache_store import AdminCacheStore

from sqlalchemy import select


QUESTION_LIST_CACHE_TTL_SECONDS = 120


class AdminQuestionService:
    def __init__(
        self,
        question_repository: QuestionBankRepository | None = None,
        audit_log_repository: AuditLogRepository | None = None,
        cache_store: AdminCacheStore | None = None,
        session_factory=AsyncSessionLocal,
    ):
        self.question_repository = question_repository or QuestionBankRepository()
        self.audit_log_repository = audit_log_repository or AuditLogRepository()
        self.cache_store = cache_store or AdminCacheStore(redis_client)
        self.session_factory = session_factory

    async def list_questions(
        self,
        *,
        course_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        cached = await self.cache_store.get_json(
            "questions-list",
            bot_id=None,
            extra_parts=(course_id, status, limit, offset),
        )
        if cached is not None:
            return cached

        questions = await self.question_repository.list_questions(
            course_id=course_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        course_ids = {q.course_id for q in questions if q.course_id}
        course_names = await self._load_course_names(course_ids)
        payload = [
            self._serialize_question(question, course_names)
            for question in questions
        ]
        await self.cache_store.set_json(
            "questions-list",
            payload,
            bot_id=None,
            extra_parts=(course_id, status, limit, offset),
            ttl_seconds=QUESTION_LIST_CACHE_TTL_SECONDS,
        )
        return payload

    async def update_question(
        self,
        question_key: str,
        payload: dict,
        *,
        actor_staff_user_id: int | None = None,
        active_bot_id: str | None = None,
    ) -> dict | None:
        before = await self.question_repository.get_question(question_key)
        if before is None:
            return None

        updates = {
            key: payload[key]
            for key in (
                "question_text",
                "correct_option_text",
                "short_explanation",
                "question_type",
                "status",
                "options",
                "band",
                "topic_id",
                "cognitive_level",
            )
            if key in payload
        }
        after_model = await self.question_repository.update_question(question_key, updates)
        if after_model is None:
            return None

        before_payload = self._serialize_question(before)
        after_payload = self._serialize_question(after_model)
        await self.audit_log_repository.create_audit_log(
            action="question.updated",
            entity_type="question_bank",
            entity_id=question_key,
            actor_staff_user_id=actor_staff_user_id,
            before_data=before_payload,
            after_data=after_payload,
        )
        await self.cache_store.bump_version("questions-list", bot_id=None)
        await self.cache_store.bump_version("reports-list", bot_id=active_bot_id)
        await self.cache_store.bump_version("reports-detail", bot_id=active_bot_id)
        return after_payload

    async def _load_course_names(self, course_ids: set[str]) -> dict[str, str]:
        if not course_ids:
            return {}
        async with self.session_factory() as session:
            result = await session.execute(
                select(CatalogCourse).where(CatalogCourse.code.in_(sorted(course_ids)))
            )
            return {course.code: course.name for course in result.scalars().all()}

    def _humanize_code(self, value: str | None) -> str:
        if not value:
            return ""
        return str(value).replace("-", " ").replace("_", " ").title()

    def _serialize_question(self, question, course_names: dict[str, str] | None = None) -> dict:
        course_id = question.course_id
        resolved_name = ""
        if course_names and course_id in course_names:
            resolved_name = course_names[course_id]
        else:
            resolved_name = self._humanize_code(course_id)
        return {
            "id": getattr(question, "id", 0),
            "question_key": question.question_key,
            "course_id": question.course_id,
            "course_slug": question.course_slug,
            "course_name": resolved_name,
            "question_text": question.question_text,
            "options": list(getattr(question, "options", []) or []),
            "correct_option_text": question.correct_option_text,
            "short_explanation": question.short_explanation,
            "question_type": getattr(question, "question_type", "MCQ"),
            "option_count": getattr(question, "option_count", 0),
            "status": question.status,
            "scaled_score": question.scaled_score,
            "band": question.band,
            "topic_id": getattr(question, "topic_id", ""),
            "cognitive_level": getattr(question, "cognitive_level", None),
            "updated_at": (
                question.updated_at.isoformat()
                if getattr(question, "updated_at", None)
                else None
            ),
            "has_latex": bool(getattr(question, "has_latex", False)),
            "base_score": getattr(question, "base_score", None),
            "note_reference": getattr(question, "note_reference", None),
            "distractor_complexity": getattr(question, "distractor_complexity", None),
            "processing_complexity": getattr(question, "processing_complexity", None),
            "negative_stem": getattr(question, "negative_stem", None),
            "raw_score": getattr(question, "raw_score", None),
        }
