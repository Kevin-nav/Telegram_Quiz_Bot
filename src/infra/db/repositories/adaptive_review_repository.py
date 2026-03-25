from __future__ import annotations

from sqlalchemy import select

from src.infra.db.models.adaptive_review_flag import AdaptiveReviewFlag
from src.infra.db.session import AsyncSessionLocal


class AdaptiveReviewRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get_open_flag(
        self, question_id: int, flag_type: str
    ) -> AdaptiveReviewFlag | None:
        async with self.session_factory() as session:
            return await self._get_open_flag(session, question_id, flag_type)

    async def list_open_flags(self, question_id: int) -> list[AdaptiveReviewFlag]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(AdaptiveReviewFlag).where(
                    AdaptiveReviewFlag.question_id == question_id,
                    AdaptiveReviewFlag.status == "open",
                )
            )
            return list(result.scalars().all())

    async def create_or_update_open_flag(
        self,
        *,
        question_id: int,
        flag_type: str,
        reason: str,
        suggestion: str | None = None,
        metadata: dict | None = None,
    ) -> AdaptiveReviewFlag:
        async with self.session_factory() as session:
            flag = await self._get_open_flag(session, question_id, flag_type)
            if flag is None:
                flag = AdaptiveReviewFlag(
                    question_id=question_id,
                    flag_type=flag_type,
                    reason=reason,
                    suggestion=suggestion,
                    status="open",
                    flag_metadata=metadata or {},
                )
                session.add(flag)
            else:
                flag.reason = reason
                flag.suggestion = suggestion
                flag.status = "open"
                flag.flag_metadata = metadata or {}

            await session.commit()
            await session.refresh(flag)
            return flag

    async def resolve_flag(self, question_id: int, flag_type: str) -> AdaptiveReviewFlag | None:
        async with self.session_factory() as session:
            flag = await self._get_open_flag(session, question_id, flag_type)
            if flag is None:
                return None

            flag.status = "resolved"
            from datetime import datetime, timezone

            flag.resolved_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(flag)
            return flag

    async def _get_open_flag(
        self, session, question_id: int, flag_type: str
    ) -> AdaptiveReviewFlag | None:
        result = await session.execute(
            select(AdaptiveReviewFlag).where(
                AdaptiveReviewFlag.question_id == question_id,
                AdaptiveReviewFlag.flag_type == flag_type,
                AdaptiveReviewFlag.status == "open",
            )
        )
        return result.scalar_one_or_none()
