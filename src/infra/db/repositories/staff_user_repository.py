from __future__ import annotations

from sqlalchemy import select
from sqlalchemy import delete

from src.infra.db.models.permission import Permission
from src.infra.db.models.staff_role import StaffRole
from src.infra.db.models.staff_user_permission import StaffUserPermission
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

    async def list_staff_users(self) -> list[StaffUser]:
        async with self.session_factory() as session:
            result = await session.execute(select(StaffUser).order_by(StaffUser.email.asc()))
            return list(result.scalars().all())

    async def create_staff_user(
        self,
        *,
        email: str,
        display_name: str | None = None,
        is_active: bool = True,
    ) -> StaffUser:
        async with self.session_factory() as session:
            staff_user = StaffUser(
                email=email,
                display_name=display_name,
                is_active=is_active,
            )
            session.add(staff_user)
            await session.commit()
            await session.refresh(staff_user)
            return staff_user

    async def update_staff_user(
        self,
        staff_user_id: int,
        **updates,
    ) -> StaffUser | None:
        async with self.session_factory() as session:
            staff_user = await session.get(StaffUser, staff_user_id)
            if staff_user is None:
                return None

            for field in ("email", "display_name", "is_active"):
                if field in updates and updates[field] is not None:
                    setattr(staff_user, field, updates[field])

            await session.commit()
            await session.refresh(staff_user)
            return staff_user

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

    async def replace_roles_for_user(
        self, staff_user_id: int, role_codes: list[str]
    ) -> list[str]:
        unique_codes = list(dict.fromkeys(role_codes))

        async with self.session_factory() as session:
            await session.execute(
                delete(StaffUserRole).where(StaffUserRole.staff_user_id == staff_user_id)
            )
            if unique_codes:
                result = await session.execute(
                    select(StaffRole).where(StaffRole.code.in_(unique_codes))
                )
                roles = list(result.scalars().all())
                role_map = {role.code: role for role in roles}
                session.add_all(
                    [
                        StaffUserRole(
                            staff_user_id=staff_user_id,
                            staff_role_id=role_map[code].id,
                        )
                        for code in unique_codes
                        if code in role_map
                    ]
                )
                await session.commit()
                return [code for code in unique_codes if code in role_map]

            await session.commit()
            return []

    async def replace_permissions_for_user(
        self, staff_user_id: int, permission_codes: list[str]
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
