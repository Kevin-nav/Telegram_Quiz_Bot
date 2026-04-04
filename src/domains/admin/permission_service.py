from __future__ import annotations

from src.bot.runtime_config import ADARKWA_BOT_ID, TANJAH_BOT_ID
from src.infra.db.repositories.catalog_repository import CatalogRepository
from src.infra.db.repositories.permission_repository import PermissionRepository
from src.infra.db.repositories.staff_catalog_access_repository import (
    StaffCatalogAccessRepository,
)
from src.infra.db.repositories.staff_user_repository import StaffUserRepository


class PermissionService:
    def __init__(
        self,
        staff_user_repository: StaffUserRepository | None = None,
        permission_repository: PermissionRepository | None = None,
        staff_catalog_access_repository: StaffCatalogAccessRepository | None = None,
        catalog_repository: CatalogRepository | None = None,
    ):
        self.staff_user_repository = staff_user_repository or StaffUserRepository()
        self.permission_repository = permission_repository or PermissionRepository()
        self.staff_catalog_access_repository = (
            staff_catalog_access_repository or StaffCatalogAccessRepository()
        )
        self.catalog_repository = catalog_repository or CatalogRepository()

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

    async def user_can_access_bot_catalog_scope(
        self,
        staff_user_id: int,
        bot_id: str | None,
        *,
        program_code: str | None = None,
        level_code: str | None = None,
        course_code: str | None = None,
    ) -> bool:
        if bot_id not in {ADARKWA_BOT_ID, TANJAH_BOT_ID}:
            return True

        staff_user = await self.staff_user_repository.get_by_id(staff_user_id)
        if staff_user is None or not staff_user.is_active:
            return False

        role_codes = await self.staff_user_repository.list_role_codes_for_user(
            staff_user_id
        )
        if "super_admin" in role_codes:
            return True

        catalog_access = (
            await self.staff_catalog_access_repository.list_catalog_access_for_user(
                staff_user_id
            )
        )
        if not catalog_access:
            return True

        for grant in catalog_access:
            if grant.get("bot_id") != bot_id:
                continue
            if await self._grant_matches_catalog_scope(
                grant,
                program_code=program_code,
                level_code=level_code,
                course_code=course_code,
            ):
                return True
        return False

    async def _grant_matches_catalog_scope(
        self,
        grant: dict,
        *,
        program_code: str | None,
        level_code: str | None,
        course_code: str | None,
    ) -> bool:
        grant_program_code = grant.get("program_code")
        grant_level_code = grant.get("level_code")
        grant_course_code = grant.get("course_code")

        if grant_course_code:
            if course_code:
                return course_code == grant_course_code
            return (
                program_code in {None, grant_program_code}
                and level_code in {None, grant_level_code}
            )

        if grant_program_code and program_code and grant_program_code != program_code:
            return False
        if grant_level_code and level_code and grant_level_code != level_code:
            return False

        if course_code and grant_program_code and grant_level_code:
            offerings = await self.catalog_repository.list_offerings(
                program_code=grant_program_code,
                level_code=grant_level_code,
                course_code=course_code,
            )
            return bool(offerings)

        return True
