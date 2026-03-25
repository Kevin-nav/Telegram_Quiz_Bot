from __future__ import annotations

from dataclasses import dataclass

from src.infra.db.models.staff_user import StaffUser
from src.infra.db.repositories.staff_user_repository import StaffUserRepository


@dataclass(slots=True)
class AdminPrincipal:
    staff_user_id: int
    email: str
    display_name: str | None = None


class AuthService:
    def __init__(self, staff_user_repository: StaffUserRepository | None = None):
        self.staff_user_repository = staff_user_repository or StaffUserRepository()

    async def get_staff_user(self, staff_user_id: int) -> StaffUser | None:
        return await self.staff_user_repository.get_by_id(staff_user_id)

    async def get_principal(self, staff_user_id: int) -> AdminPrincipal | None:
        staff_user = await self.get_staff_user(staff_user_id)
        if staff_user is None or not staff_user.is_active:
            return None

        return AdminPrincipal(
            staff_user_id=staff_user.id,
            email=staff_user.email,
            display_name=staff_user.display_name,
        )
