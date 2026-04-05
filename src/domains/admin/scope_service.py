from __future__ import annotations

from src.core.config import settings
from src.infra.db.repositories.catalog_repository import CatalogRepository
from src.infra.db.repositories.staff_catalog_access_repository import (
    StaffCatalogAccessRepository,
)


class AdminScopeService:
    def __init__(
        self,
        *,
        catalog_repository: CatalogRepository | None = None,
        staff_catalog_access_repository: StaffCatalogAccessRepository | None = None,
    ):
        self.catalog_repository = catalog_repository or CatalogRepository()
        self.staff_catalog_access_repository = (
            staff_catalog_access_repository or StaffCatalogAccessRepository()
        )

    async def resolve_course_codes_for_principal(self, principal) -> set[str] | None:
        bot_id = self.resolve_active_bot_id(principal)
        role_codes = set(getattr(principal, "role_codes", []) or [])
        bot_allowed_course_codes = self._bot_allowed_course_codes(bot_id)

        if "super_admin" in role_codes:
            return bot_allowed_course_codes

        if not bot_id:
            return bot_allowed_course_codes

        entries = await self.staff_catalog_access_repository.list_catalog_access_for_user(
            getattr(principal, "staff_user_id")
        )
        bot_entries = [entry for entry in entries if entry.get("bot_id") == bot_id]
        if not bot_entries:
            return bot_allowed_course_codes

        scoped_course_codes: set[str] = set()
        for entry in bot_entries:
            # A grant with no narrower selectors means full access within the bot.
            if not any(
                entry.get(field) for field in ("program_code", "level_code", "course_code")
            ):
                return bot_allowed_course_codes

            course_code = entry.get("course_code")
            if course_code:
                scoped_course_codes.add(str(course_code))
                continue

            offerings = await self.catalog_repository.list_offerings(
                program_code=entry.get("program_code"),
                level_code=entry.get("level_code"),
            )
            scoped_course_codes.update(offering.course_code for offering in offerings)

        if bot_allowed_course_codes is not None:
            scoped_course_codes &= bot_allowed_course_codes

        return scoped_course_codes

    def resolve_active_bot_id(self, principal) -> str | None:
        bot_id = getattr(principal, "active_bot_id", None)
        if not bot_id:
            return None
        if bot_id not in settings.bot_configs:
            return None
        return str(bot_id)

    def _bot_allowed_course_codes(self, bot_id: str | None) -> set[str] | None:
        if not bot_id:
            return None

        bot_config = settings.bot_configs.get(bot_id)
        allowed_course_codes = getattr(bot_config, "allowed_course_codes", ()) if bot_config else ()
        if not allowed_course_codes:
            return None

        return set(allowed_course_codes)
