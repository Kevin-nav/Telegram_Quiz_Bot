from __future__ import annotations

from src.infra.db.repositories.audit_log_repository import AuditLogRepository
from src.infra.db.repositories.permission_repository import PermissionRepository
from src.infra.db.repositories.staff_user_repository import StaffUserRepository


class AdminStaffService:
    def __init__(
        self,
        staff_user_repository: StaffUserRepository | None = None,
        permission_repository: PermissionRepository | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ):
        self.staff_user_repository = staff_user_repository or StaffUserRepository()
        self.permission_repository = permission_repository or PermissionRepository()
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
        existing = await self.staff_user_repository.get_by_email(normalized["email"])
        if existing is None:
            staff_user = await self.staff_user_repository.create_staff_user(
                email=normalized["email"],
                display_name=normalized["display_name"],
                is_active=normalized["is_active"],
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

        updates = {}
        for field in ("email", "display_name", "is_active"):
            if field in payload:
                updates[field] = payload[field]

        staff_user = await self.staff_user_repository.update_staff_user(
            staff_user_id,
            **updates,
        )
        if staff_user is None:
            return None

        if "role_codes" in payload:
            await self.staff_user_repository.replace_roles_for_user(
                staff_user_id,
                self._normalize_codes(payload.get("role_codes")),
            )
        if "permission_codes" in payload:
            await self.permission_repository.replace_direct_permissions_for_user(
                staff_user_id,
                self._normalize_codes(payload.get("permission_codes")),
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

    async def _serialize_staff_user(self, staff_user) -> dict:
        role_codes = await self.staff_user_repository.list_role_codes_for_user(
            staff_user.id
        )
        permission_codes = (
            await self.permission_repository.list_direct_permission_codes_for_user(
                staff_user.id
            )
        )
        return {
            "staff_user_id": staff_user.id,
            "email": staff_user.email,
            "display_name": staff_user.display_name,
            "is_active": bool(getattr(staff_user, "is_active", True)),
            "role_codes": role_codes,
            "permission_codes": permission_codes,
        }

    async def _sync_assignments(
        self,
        staff_user_id: int,
        *,
        role_codes: list[str],
        permission_codes: list[str],
    ) -> None:
        await self.staff_user_repository.replace_roles_for_user(staff_user_id, role_codes)
        await self.permission_repository.replace_direct_permissions_for_user(
            staff_user_id,
            permission_codes,
        )

    def _normalize_payload(self, payload: dict) -> dict:
        return {
            "email": str(payload["email"]).strip(),
            "display_name": payload.get("display_name"),
            "is_active": bool(payload.get("is_active", True)),
            "role_codes": self._normalize_codes(payload.get("role_codes")),
            "permission_codes": self._normalize_codes(payload.get("permission_codes")),
        }

    def _normalize_codes(self, value) -> list[str]:
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if item is not None]
        return [str(value)]
