from __future__ import annotations

from datetime import UTC, datetime

from src.bot.runtime_config import ADARKWA_BOT_ID, TANJAH_BOT_ID
from src.domains.admin.password_service import PasswordService
from src.infra.db.repositories.admin_session_repository import AdminSessionRepository
from src.infra.db.repositories.audit_log_repository import AuditLogRepository
from src.infra.db.repositories.permission_repository import PermissionRepository
from src.infra.db.repositories.staff_bot_access_repository import (
    StaffBotAccessRepository,
)
from src.infra.db.repositories.staff_catalog_access_repository import (
    StaffCatalogAccessRepository,
)
from src.infra.db.repositories.staff_user_repository import StaffUserRepository


KNOWN_ADMIN_BOT_IDS = (ADARKWA_BOT_ID, TANJAH_BOT_ID)


class AdminStaffService:
    def __init__(
        self,
        staff_user_repository: StaffUserRepository | None = None,
        permission_repository: PermissionRepository | None = None,
        staff_bot_access_repository: StaffBotAccessRepository | None = None,
        staff_catalog_access_repository: StaffCatalogAccessRepository | None = None,
        admin_session_repository: AdminSessionRepository | None = None,
        password_service: PasswordService | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ):
        self.staff_user_repository = staff_user_repository or StaffUserRepository()
        self.permission_repository = permission_repository or PermissionRepository()
        self.staff_bot_access_repository = (
            staff_bot_access_repository or StaffBotAccessRepository()
        )
        self.staff_catalog_access_repository = (
            staff_catalog_access_repository or StaffCatalogAccessRepository()
        )
        self.admin_session_repository = (
            admin_session_repository or AdminSessionRepository()
        )
        self.password_service = password_service or PasswordService()
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    async def list_staff_users(self) -> list[dict]:
        staff_users = await self.staff_user_repository.list_staff_users()
        return [await self._serialize_staff_user(staff_user) for staff_user in staff_users]

    async def get_staff_user(self, staff_user_id: int) -> dict | None:
        staff_user = await self.staff_user_repository.get_by_id(staff_user_id)
        if staff_user is None:
            return None
        return await self._serialize_staff_user(staff_user)

    async def create_staff_user(
        self,
        payload: dict,
        *,
        actor_staff_user_id: int | None = None,
    ) -> dict:
        normalized = self._normalize_payload(payload)
        self._validate_bot_access(
            normalized["role_codes"],
            normalized["bot_access"],
        )
        normalized["catalog_access"] = self._normalize_catalog_access(
            payload.get("catalog_access"),
            normalized["bot_access"],
        )
        existing = await self.staff_user_repository.get_by_email(normalized["email"])
        if existing is None:
            if not normalized["temporary_password"]:
                raise ValueError("A temporary password is required for new staff users.")
            staff_user = await self.staff_user_repository.create_staff_user(
                email=normalized["email"],
                display_name=normalized["display_name"],
                is_active=normalized["is_active"],
                password_hash=self.password_service.hash_password(
                    normalized["temporary_password"]
                ),
                must_change_password=True,
                last_selected_bot_id=normalized["bot_access"][0],
            )
        else:
            staff_user = await self.staff_user_repository.update_staff_user(
                existing.id,
                email=normalized["email"],
                display_name=normalized["display_name"],
                is_active=normalized["is_active"],
            )

        if staff_user is None:
            return {}

        await self._sync_assignments(
            staff_user.id,
            role_codes=normalized["role_codes"],
            permission_codes=normalized["permission_codes"],
            bot_access=normalized["bot_access"],
            catalog_access=normalized["catalog_access"],
        )

        staff_user_payload = await self.get_staff_user(staff_user.id)
        await self.audit_log_repository.create_audit_log(
            action="staff.created",
            entity_type="staff_users",
            entity_id=str(staff_user.id),
            actor_staff_user_id=actor_staff_user_id,
            after_data=staff_user_payload,
        )
        return staff_user_payload

    async def update_staff_user(
        self,
        staff_user_id: int,
        payload: dict,
        *,
        actor_staff_user_id: int | None = None,
    ) -> dict | None:
        before = await self.get_staff_user(staff_user_id)
        if before is None:
            return None

        role_codes = (
            self._normalize_codes(payload.get("role_codes"))
            if "role_codes" in payload
            else list(before["role_codes"])
        )
        bot_access = (
            self._normalize_bot_access(payload.get("bot_access"))
            if "bot_access" in payload
            else list(before["bot_access"])
        )
        self._validate_bot_access(role_codes, bot_access)
        catalog_access = (
            self._normalize_catalog_access(
                payload.get("catalog_access"),
                bot_access,
            )
            if "catalog_access" in payload
            else list(before["catalog_access"])
        )

        updates = {}
        for field in ("email", "display_name", "is_active"):
            if field in payload:
                updates[field] = payload[field]
        if "bot_access" in payload and bot_access:
            updates["last_selected_bot_id"] = bot_access[0]

        staff_user = await self.staff_user_repository.update_staff_user(
            staff_user_id,
            **updates,
        )
        if staff_user is None:
            return None

        if "role_codes" in payload:
            await self.staff_user_repository.replace_roles_for_user(
                staff_user_id,
                role_codes,
            )
        if "permission_codes" in payload:
            await self.permission_repository.replace_direct_permissions_for_user(
                staff_user_id,
                self._normalize_codes(payload.get("permission_codes")),
            )
        if "bot_access" in payload:
            await self.staff_bot_access_repository.replace_bot_access_for_user(
                staff_user_id,
                bot_access,
            )
        if "catalog_access" in payload:
            await self.staff_catalog_access_repository.replace_catalog_access_for_user(
                staff_user_id,
                catalog_access,
            )

        after = await self.get_staff_user(staff_user_id)
        await self.audit_log_repository.create_audit_log(
            action="staff.updated",
            entity_type="staff_users",
            entity_id=str(staff_user_id),
            actor_staff_user_id=actor_staff_user_id,
            before_data=before,
            after_data=after,
        )
        return after

    async def reset_staff_password(
        self,
        staff_user_id: int,
        temporary_password: str,
        *,
        actor_staff_user_id: int | None = None,
    ) -> dict | None:
        before = await self.get_staff_user(staff_user_id)
        if before is None:
            return None
        if len(temporary_password) < 8:
            raise ValueError("Temporary password must be at least 8 characters.")

        staff_user = await self.staff_user_repository.update_password(
            staff_user_id,
            password_hash=self.password_service.hash_password(temporary_password),
            must_change_password=True,
            password_updated_at=datetime.now(UTC),
        )
        if staff_user is None:
            return None

        await self.admin_session_repository.revoke_sessions_for_user(
            staff_user_id,
            revoked_at=datetime.now(UTC),
        )

        after = await self.get_staff_user(staff_user_id)
        await self.audit_log_repository.create_audit_log(
            action="staff.password_reset",
            entity_type="staff_users",
            entity_id=str(staff_user_id),
            actor_staff_user_id=actor_staff_user_id,
            before_data=before,
            after_data=after,
        )
        return after

    async def _serialize_staff_user(self, staff_user) -> dict:
        role_codes = await self.staff_user_repository.list_role_codes_for_user(
            staff_user.id
        )
        permission_codes = (
            await self.permission_repository.list_direct_permission_codes_for_user(
                staff_user.id
            )
        )
        bot_access = (
            await self.staff_bot_access_repository.list_active_bot_ids_for_user(
                staff_user.id
            )
        )
        catalog_access = (
            await self.staff_catalog_access_repository.list_catalog_access_for_user(
                staff_user.id
            )
        )
        return {
            "staff_user_id": staff_user.id,
            "id": staff_user.id,
            "email": staff_user.email,
            "display_name": staff_user.display_name,
            "is_active": bool(getattr(staff_user, "is_active", True)),
            "must_change_password": bool(
                getattr(staff_user, "must_change_password", False)
            ),
            "role_codes": role_codes,
            "roles": role_codes,
            "permission_codes": permission_codes,
            "permissions": permission_codes,
            "bot_access": bot_access,
            "catalog_access": catalog_access,
        }

    async def _sync_assignments(
        self,
        staff_user_id: int,
        *,
        role_codes: list[str],
        permission_codes: list[str],
        bot_access: list[str],
        catalog_access: list[dict],
    ) -> None:
        await self.staff_user_repository.replace_roles_for_user(staff_user_id, role_codes)
        await self.permission_repository.replace_direct_permissions_for_user(
            staff_user_id,
            permission_codes,
        )
        await self.staff_bot_access_repository.replace_bot_access_for_user(
            staff_user_id,
            bot_access,
        )
        await self.staff_catalog_access_repository.replace_catalog_access_for_user(
            staff_user_id,
            catalog_access,
        )

    def _normalize_payload(self, payload: dict) -> dict:
        return {
            "email": str(payload["email"]).strip(),
            "display_name": payload.get("display_name"),
            "is_active": bool(payload.get("is_active", True)),
            "role_codes": self._normalize_codes(payload.get("role_codes")),
            "permission_codes": self._normalize_codes(payload.get("permission_codes")),
            "bot_access": self._normalize_bot_access(payload.get("bot_access")),
            "temporary_password": (
                str(payload.get("temporary_password"))
                if payload.get("temporary_password")
                else None
            ),
        }

    def _normalize_codes(self, value) -> list[str]:
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if item is not None]
        return [str(value)]

    def _normalize_bot_access(self, value) -> list[str]:
        bot_ids = self._normalize_codes(value)
        if not bot_ids:
            return []
        normalized = [bot_id.strip() for bot_id in bot_ids if bot_id.strip()]
        return [bot_id for bot_id in dict.fromkeys(normalized)]

    def _validate_bot_access(
        self,
        role_codes: list[str],
        bot_access: list[str],
    ) -> None:
        unknown_bot_ids = [
            bot_id for bot_id in bot_access if bot_id not in KNOWN_ADMIN_BOT_IDS
        ]
        if unknown_bot_ids:
            raise ValueError(f"Unknown bot workspace(s): {', '.join(unknown_bot_ids)}")

        if "super_admin" in role_codes:
            if not bot_access:
                raise ValueError("Super admins must have at least one bot workspace.")
            return

        if len(bot_access) != 1:
            raise ValueError("Non-super-admin users must be assigned exactly one bot workspace.")

    def _normalize_catalog_access(
        self,
        value,
        bot_access: list[str],
    ) -> list[dict]:
        if not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise ValueError("catalog_access must be a list of scope objects.")

        normalized_entries = []
        for entry in value:
            if not isinstance(entry, dict):
                raise ValueError("catalog_access entries must be objects.")

            bot_id = str(entry.get("bot_id") or "").strip()
            if not bot_id and len(bot_access) == 1:
                bot_id = bot_access[0]
            if bot_id not in bot_access:
                raise ValueError(
                    f"Catalog scope bot_id must be one of this user's bot assignments: {bot_access}."
                )

            program_code = (
                str(entry.get("program_code")).strip()
                if entry.get("program_code")
                else None
            )
            level_code = (
                str(entry.get("level_code")).strip()
                if entry.get("level_code")
                else None
            )
            course_code = (
                str(entry.get("course_code")).strip()
                if entry.get("course_code")
                else None
            )
            normalized_entries.append(
                {
                    "bot_id": bot_id,
                    "program_code": program_code,
                    "level_code": level_code,
                    "course_code": course_code,
                }
            )

        deduped = []
        seen = set()
        for entry in normalized_entries:
            key = (
                entry["bot_id"],
                entry["program_code"],
                entry["level_code"],
                entry["course_code"],
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(entry)
        return deduped
