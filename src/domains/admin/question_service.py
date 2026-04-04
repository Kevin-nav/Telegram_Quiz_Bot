from __future__ import annotations

from src.infra.db.repositories.audit_log_repository import AuditLogRepository
from src.infra.db.repositories.question_bank_repository import QuestionBankRepository


class AdminQuestionService:
    def __init__(
        self,
        question_repository: QuestionBankRepository | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ):
        self.question_repository = question_repository or QuestionBankRepository()
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    async def list_questions(
        self,
        *,
        course_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        questions = await self.question_repository.list_questions(
            course_id=course_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [self._serialize_question(question) for question in questions]

    async def update_question(
        self,
        question_key: str,
        payload: dict,
        *,
        actor_staff_user_id: int | None = None,
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
        return after_payload

    def _serialize_question(self, question) -> dict:
        return {
            "id": getattr(question, "id", 0),
            "question_key": question.question_key,
            "course_id": question.course_id,
            "course_slug": question.course_slug,
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
