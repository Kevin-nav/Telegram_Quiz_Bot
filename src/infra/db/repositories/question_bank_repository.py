from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.bot.runtime_config import TANJAH_BOT_ID
from src.infra.db.models.question_asset_variant import QuestionAssetVariant
from src.infra.db.models.question_bank import QuestionBank
from src.infra.db.session import AsyncSessionLocal


class QuestionBankRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def upsert_question(self, payload: dict) -> QuestionBank:
        async with self.session_factory() as session:
            question = await self._get_question_by_key(session, payload["question_key"])
            if question is None:
                question = QuestionBank(**payload)
                session.add(question)
            else:
                self._apply_updates(question, payload)

            await session.commit()
            await session.refresh(question)
            return question

    async def replace_asset_variants(
        self,
        question_id: int,
        variants: Sequence[dict],
        *,
        bot_id: str = TANJAH_BOT_ID,
    ) -> list[QuestionAssetVariant]:
        async with self.session_factory() as session:
            await session.execute(
                delete(QuestionAssetVariant).where(
                    QuestionAssetVariant.question_id == question_id,
                    QuestionAssetVariant.bot_id == bot_id,
                )
            )

            records = [
                QuestionAssetVariant(
                    question_id=question_id,
                    bot_id=bot_id,
                    **{key: value for key, value in variant.items() if key != "bot_id"},
                )
                for variant in variants
            ]
            if records:
                session.add_all(records)

            await session.commit()
            for record in records:
                await session.refresh(record)
            return records

    async def list_ready_questions(self, course_id: str) -> list[QuestionBank]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(QuestionBank)
                .options(selectinload(QuestionBank.asset_variants))
                .where(
                    QuestionBank.course_id == course_id,
                    QuestionBank.status == "ready",
                )
                .order_by(QuestionBank.id.asc())
            )
            return list(result.scalars().all())

    async def get_question(self, question_key: str) -> QuestionBank | None:
        async with self.session_factory() as session:
            return await self._get_question_by_key(session, question_key)

    async def list_questions(
        self,
        *,
        course_id: str | None = None,
        status: str | None = None,
        course_codes: set[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QuestionBank]:
        async with self.session_factory() as session:
            stmt = select(QuestionBank)
            if course_codes is not None:
                if not course_codes:
                    return []
                stmt = stmt.where(QuestionBank.course_id.in_(sorted(course_codes)))
            if course_id is not None:
                stmt = stmt.where(QuestionBank.course_id == course_id)
            if status is not None:
                stmt = stmt.where(QuestionBank.status == status)
            stmt = stmt.order_by(QuestionBank.id.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_question_status(
        self,
        question_key: str,
        *,
        status: str,
        source_checksum: str | None = None,
        render_checksum: str | None = None,
        explanation_asset_key: str | None = None,
        explanation_asset_url: str | None = None,
        explanation_asset_keys_by_bot: dict[str, str] | None = None,
        explanation_asset_urls_by_bot: dict[str, str] | None = None,
        variant_count: int | None = None,
    ) -> QuestionBank | None:
        async with self.session_factory() as session:
            question = await self._get_question_by_key(session, question_key)
            if question is None:
                return None

            updates = {
                "status": status,
                "source_checksum": source_checksum,
                "render_checksum": render_checksum,
                "explanation_asset_key": explanation_asset_key,
                "explanation_asset_url": explanation_asset_url,
                "explanation_asset_keys_by_bot": explanation_asset_keys_by_bot,
                "explanation_asset_urls_by_bot": explanation_asset_urls_by_bot,
                "variant_count": variant_count,
            }
            self._apply_updates(
                question,
                {key: value for key, value in updates.items() if value is not None},
            )
            await session.commit()
            await session.refresh(question)
            return question

    async def update_question(
        self, question_key: str, updates: dict
    ) -> QuestionBank | None:
        async with self.session_factory() as session:
            question = await self._get_question_by_key(session, question_key)
            if question is None:
                return None

            self._apply_updates(
                question,
                {key: value for key, value in updates.items() if value is not None},
            )
            await session.commit()
            await session.refresh(question)
            return question

    async def _get_question_by_key(self, session, question_key: str) -> QuestionBank | None:
        result = await session.execute(
            select(QuestionBank)
            .options(selectinload(QuestionBank.asset_variants))
            .where(QuestionBank.question_key == question_key)
        )
        return result.scalar_one_or_none()

    def _apply_updates(self, record, payload: dict) -> None:
        for key, value in payload.items():
            setattr(record, key, value)
