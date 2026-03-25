from __future__ import annotations

from src.infra.db.repositories.permission_repository import PermissionRepository
from src.infra.db.repositories.staff_user_repository import StaffUserRepository


class PermissionService:
    def __init__(
        self,
        staff_user_repository: StaffUserRepository | None = None,
        permission_repository: PermissionRepository | None = None,
    ):
        self.staff_user_repository = staff_user_repository or StaffUserRepository()
        self.permission_repository = permission_repository or PermissionRepository()

    async def get_effective_permission_codes(self, staff_user_id: int) -> set[str]:
        staff_user = await self.staff_user_repository.get_by_id(staff_user_id)
        if staff_user is None or not staff_user.is_active:
            return set()

        codes = await self.permission_repository.list_effective_permission_codes_for_user(
            staff_user_id
        )
        return set(codes)

    async def user_has_permission(self, staff_user_id: int, permission_code: str) -> bool:
        effective_permission_codes = await self.get_effective_permission_codes(staff_user_id)
        return permission_code in effective_permission_codes
