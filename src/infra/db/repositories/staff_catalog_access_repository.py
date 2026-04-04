from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, select

from src.infra.db.models.staff_catalog_access import StaffCatalogAccess
from src.infra.db.session import AsyncSessionLocal


class StaffCatalogAccessRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def list_catalog_access_for_user(self, staff_user_id: int) -> list[dict]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(StaffCatalogAccess)
                .where(
                    StaffCatalogAccess.staff_user_id == staff_user_id,
                    StaffCatalogAccess.is_active.is_(True),
                )
                .order_by(
                    StaffCatalogAccess.bot_id.asc(),
                    StaffCatalogAccess.program_code.asc(),
                    StaffCatalogAccess.level_code.asc(),
                    StaffCatalogAccess.course_code.asc(),
                )
            )
            return [
                {
                    "bot_id": item.bot_id,
                    "program_code": item.program_code,
                    "level_code": item.level_code,
                    "course_code": item.course_code,
                }
                for item in result.scalars().all()
            ]

    async def replace_catalog_access_for_user(
        self,
        staff_user_id: int,
        entries: Sequence[dict],
    ) -> list[dict]:
        normalized_entries = []
        seen = set()
        for entry in entries:
            normalized = {
                "bot_id": entry.get("bot_id"),
                "program_code": entry.get("program_code"),
                "level_code": entry.get("level_code"),
                "course_code": entry.get("course_code"),
            }
            key = tuple(normalized.items())
            if key in seen:
                continue
            seen.add(key)
            normalized_entries.append(normalized)

        async with self.session_factory() as session:
            await session.execute(
                delete(StaffCatalogAccess).where(
                    StaffCatalogAccess.staff_user_id == staff_user_id
                )
            )
            if normalized_entries:
                session.add_all(
                    [
                        StaffCatalogAccess(
                            staff_user_id=staff_user_id,
                            bot_id=str(entry["bot_id"]),
                            program_code=entry["program_code"],
                            level_code=entry["level_code"],
                            course_code=entry["course_code"],
                            is_active=True,
                        )
                        for entry in normalized_entries
                    ]
                )
            await session.commit()
        return normalized_entries
