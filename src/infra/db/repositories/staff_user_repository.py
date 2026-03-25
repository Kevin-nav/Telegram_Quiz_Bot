from __future__ import annotations

from sqlalchemy import select

from src.infra.db.models.staff_role import StaffRole
from src.infra.db.models.staff_user import StaffUser
from src.infra.db.models.staff_user_role import StaffUserRole
from src.infra.db.session import AsyncSessionLocal


class StaffUserRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get_by_id(self, staff_user_id: int) -> StaffUser | None:
        async with self.session_factory() as session:
            return await session.get(StaffUser, staff_user_id)

    async def get_by_email(self, email: str) -> StaffUser | None:
        async with self.session_factory() as session:
            result = await session.execute(
                select(StaffUser).where(StaffUser.email == email)
            )
            return result.scalar_one_or_none()

    async def list_roles_for_user(self, staff_user_id: int) -> list[StaffRole]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(StaffRole)
                .join(StaffUserRole, StaffUserRole.staff_role_id == StaffRole.id)
                .where(StaffUserRole.staff_user_id == staff_user_id)
                .order_by(StaffRole.code.asc())
            )
            return list(result.scalars().all())

    async def list_role_codes_for_user(self, staff_user_id: int) -> list[str]:
        roles = await self.list_roles_for_user(staff_user_id)
        return [role.code for role in roles]
