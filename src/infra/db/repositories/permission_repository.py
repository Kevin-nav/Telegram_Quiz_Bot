from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy import select

from src.infra.db.models.permission import Permission
from src.infra.db.models.staff_role_permission import StaffRolePermission
from src.infra.db.models.staff_user_permission import StaffUserPermission
from src.infra.db.models.staff_user_role import StaffUserRole
from src.infra.db.session import AsyncSessionLocal


class PermissionRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get_by_code(self, code: str) -> Permission | None:
        async with self.session_factory() as session:
            result = await session.execute(select(Permission).where(Permission.code == code))
            return result.scalar_one_or_none()

    async def list_direct_permission_codes_for_user(self, staff_user_id: int) -> list[str]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Permission.code)
                .join(StaffUserPermission, StaffUserPermission.permission_id == Permission.id)
                .where(StaffUserPermission.staff_user_id == staff_user_id)
                .order_by(Permission.code.asc())
            )
            return list(result.scalars().all())

    async def list_role_permission_codes_for_user(self, staff_user_id: int) -> list[str]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Permission.code)
                .join(StaffRolePermission, StaffRolePermission.permission_id == Permission.id)
                .join(
                    StaffUserRole,
                    StaffUserRole.staff_role_id == StaffRolePermission.staff_role_id,
                )
                .where(StaffUserRole.staff_user_id == staff_user_id)
                .order_by(Permission.code.asc())
            )
            return list(result.scalars().all())

    async def list_effective_permission_codes_for_user(self, staff_user_id: int) -> list[str]:
        direct_codes = await self.list_direct_permission_codes_for_user(staff_user_id)
        role_codes = await self.list_role_permission_codes_for_user(staff_user_id)
        return sorted(set(direct_codes) | set(role_codes))

    async def replace_direct_permissions_for_user(
        self, staff_user_id: int, permission_codes: Sequence[str]
    ) -> list[str]:
        unique_codes = list(dict.fromkeys(permission_codes))

        async with self.session_factory() as session:
            await session.execute(
                delete(StaffUserPermission).where(
                    StaffUserPermission.staff_user_id == staff_user_id
                )
            )
            if unique_codes:
                result = await session.execute(
                    select(Permission).where(Permission.code.in_(unique_codes))
                )
                permissions = list(result.scalars().all())
                permission_map = {permission.code: permission for permission in permissions}
                session.add_all(
                    [
                        StaffUserPermission(
                            staff_user_id=staff_user_id,
                            permission_id=permission_map[code].id,
                        )
                        for code in unique_codes
                        if code in permission_map
                    ]
                )
                await session.commit()
                return [code for code in unique_codes if code in permission_map]

            await session.commit()
            return []
