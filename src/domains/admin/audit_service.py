from __future__ import annotations

from src.infra.db.repositories.audit_log_repository import AuditLogRepository


class AdminAuditService:
    def __init__(self, audit_log_repository: AuditLogRepository | None = None):
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    async def list_audit_logs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        logs = await self.audit_log_repository.list_audit_logs(
            limit=limit,
            offset=offset,
        )
        return [self._serialize_audit_log(log_entry) for log_entry in logs]

    def _serialize_audit_log(self, log_entry) -> dict:
        created_at = getattr(log_entry, "created_at", None)
        return {
            "id": log_entry.id,
            "actor_staff_user_id": log_entry.actor_staff_user_id,
            "action": log_entry.action,
            "entity_type": log_entry.entity_type,
            "entity_id": log_entry.entity_id,
            "before_data": log_entry.before_data,
            "after_data": log_entry.after_data,
            "created_at": created_at.isoformat() if created_at is not None else None,
        }
