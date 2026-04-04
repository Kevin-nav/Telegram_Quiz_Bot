from __future__ import annotations

from sqlalchemy import delete, select

from src.infra.db.models.staff_bot_access import StaffBotAccess
from src.infra.db.session import AsyncSessionLocal


class StaffBotAccessRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def list_active_bot_ids_for_user(self, staff_user_id: int) -> list[str]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(StaffBotAccess.bot_id)
                .where(
                    StaffBotAccess.staff_user_id == staff_user_id,
                    StaffBotAccess.is_active.is_(True),
                )
                .order_by(StaffBotAccess.bot_id.asc())
            )
            return list(result.scalars().all())

    async def replace_bot_access_for_user(
        self,
        staff_user_id: int,
        bot_ids: list[str],
    ) -> list[str]:
        unique_bot_ids = [bot_id for bot_id in dict.fromkeys(bot_ids) if bot_id]

        async with self.session_factory() as session:
            await session.execute(
                delete(StaffBotAccess).where(
                    StaffBotAccess.staff_user_id == staff_user_id
                )
            )
            if unique_bot_ids:
                session.add_all(
                    [
                        StaffBotAccess(
                            staff_user_id=staff_user_id,
                            bot_id=bot_id,
                            is_active=True,
                        )
                        for bot_id in unique_bot_ids
                    ]
                )
            await session.commit()
            return unique_bot_ids
