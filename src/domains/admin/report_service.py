from __future__ import annotations

from sqlalchemy import select

from src.infra.db.models.catalog_course import CatalogCourse
from src.infra.db.models.question_bank import QuestionBank
from src.infra.db.models.question_report import QuestionReport
from src.infra.db.models.telegram_identity import TelegramIdentity
from src.infra.db.repositories.audit_log_repository import AuditLogRepository
from src.infra.db.session import AsyncSessionLocal


VALID_REPORT_STATUSES = {"open", "resolved", "dismissed"}


class AdminReportService:
    def __init__(
        self,
        *,
        session_factory=AsyncSessionLocal,
        audit_log_repository: AuditLogRepository | None = None,
    ):
        self.session_factory = session_factory
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    async def list_reports(
        self,
        *,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        reports = await self._list_reports(
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )
        open_count = sum(1 for report in reports if report.report_status == "open")
        if status:
            reports = [report for report in reports if report.report_status == status]
        reports = reports[offset : offset + limit]
        return {
            "items": await self._serialize_reports(reports),
            "count": len(reports),
            "open_count": open_count,
        }

    async def get_report(
        self,
        report_id: int,
        *,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
    ) -> dict | None:
        report = await self._get_report(
            report_id,
            active_bot_id=active_bot_id,
            course_codes=course_codes,
        )
        if report is None:
            return None
        payload = await self._serialize_reports([report])
        return payload[0] if payload else None

    async def update_report_status(
        self,
        report_id: int,
        *,
        status: str,
        actor_staff_user_id: int | None = None,
        active_bot_id: str | None = None,
        course_codes: set[str] | None = None,
    ) -> dict | None:
        normalized_status = str(status or "").strip().lower()
        if normalized_status not in VALID_REPORT_STATUSES:
            raise ValueError("Invalid report status.")

        async with self.session_factory() as session:
            report = await self._get_report_with_session(
                session,
                report_id,
                active_bot_id=active_bot_id,
                course_codes=course_codes,
            )
            if report is None:
                return None

            before = await self._serialize_reports([report])
            report.report_status = normalized_status
            await session.commit()
            await session.refresh(report)

        after = await self._serialize_reports([report])
        before_payload = before[0] if before else None
        after_payload = after[0] if after else None
        await self.audit_log_repository.create_audit_log(
            action="question_report.updated",
            entity_type="question_reports",
            entity_id=str(report_id),
            actor_staff_user_id=actor_staff_user_id,
            before_data=before_payload,
            after_data=after_payload,
        )
        return after_payload

    async def _list_reports(
        self,
        *,
        active_bot_id: str | None,
        course_codes: set[str] | None,
    ) -> list[QuestionReport]:
        if course_codes is not None and not course_codes:
            return []

        async with self.session_factory() as session:
            stmt = select(QuestionReport).order_by(
                QuestionReport.created_at.desc(),
                QuestionReport.id.desc(),
            )
            if active_bot_id is not None:
                stmt = stmt.where(QuestionReport.bot_id == active_bot_id)
            if course_codes is not None:
                stmt = stmt.where(QuestionReport.course_id.in_(sorted(course_codes)))
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _get_report(
        self,
        report_id: int,
        *,
        active_bot_id: str | None,
        course_codes: set[str] | None,
    ) -> QuestionReport | None:
        async with self.session_factory() as session:
            return await self._get_report_with_session(
                session,
                report_id,
                active_bot_id=active_bot_id,
                course_codes=course_codes,
            )

    async def _get_report_with_session(
        self,
        session,
        report_id: int,
        *,
        active_bot_id: str | None,
        course_codes: set[str] | None,
    ) -> QuestionReport | None:
        if course_codes is not None and not course_codes:
            return None

        stmt = select(QuestionReport).where(QuestionReport.id == report_id)
        if active_bot_id is not None:
            stmt = stmt.where(QuestionReport.bot_id == active_bot_id)
        if course_codes is not None:
            stmt = stmt.where(QuestionReport.course_id.in_(sorted(course_codes)))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _serialize_reports(self, reports: list[QuestionReport]) -> list[dict]:
        if not reports:
            return []

        question_ids = {report.question_id for report in reports if report.question_id is not None}
        course_codes = {report.course_id for report in reports if report.course_id}
        user_ids = {report.user_id for report in reports}

        async with self.session_factory() as session:
            question_map = await self._load_questions(session, question_ids)
            course_map = await self._load_courses(session, course_codes)
            identity_map = await self._load_identities(session, user_ids)

        payload = []
        for report in reports:
            question = question_map.get(report.question_id)
            identity = identity_map.get(report.user_id)
            payload.append(
                {
                    "id": report.id,
                    "question_id": int(report.question_id or 0),
                    "question_key": report.question_key,
                    "question_text": getattr(question, "question_text", None)
                    or report.question_key,
                    "course_name": course_map.get(report.course_id)
                    or self._humanize_code(report.course_id),
                    "student_username": getattr(identity, "username", None)
                    or f"user_{report.user_id}",
                    "student_reasoning": report.report_note
                    or self._humanize_code(report.report_reason),
                    "status": report.report_status,
                    "created_at": report.created_at.isoformat(),
                }
            )
        return payload

    async def _load_questions(self, session, question_ids: set[int]) -> dict[int, QuestionBank]:
        if not question_ids:
            return {}

        result = await session.execute(
            select(QuestionBank).where(QuestionBank.id.in_(sorted(question_ids)))
        )
        return {question.id: question for question in result.scalars().all()}

    async def _load_courses(self, session, course_codes: set[str]) -> dict[str, str]:
        if not course_codes:
            return {}

        result = await session.execute(
            select(CatalogCourse).where(CatalogCourse.code.in_(sorted(course_codes)))
        )
        return {course.code: course.name for course in result.scalars().all()}

    async def _load_identities(self, session, user_ids: set[int]) -> dict[int, TelegramIdentity]:
        if not user_ids:
            return {}

        result = await session.execute(
            select(TelegramIdentity).where(TelegramIdentity.user_id.in_(sorted(user_ids)))
        )
        return {identity.user_id: identity for identity in result.scalars().all()}

    def _humanize_code(self, value: str | None) -> str:
        if not value:
            return ""
        return str(value).replace("-", " ").replace("_", " ").title()
