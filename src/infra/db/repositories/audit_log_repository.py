from __future__ import annotations

from src.infra.db.models.audit_log import AuditLog
from src.infra.db.session import AsyncSessionLocal


class AuditLogRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def create_audit_log(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        actor_staff_user_id: int | None = None,
        before_data: dict | None = None,
        after_data: dict | None = None,
    ) -> AuditLog:
        async with self.session_factory() as session:
            log_entry = AuditLog(
                actor_staff_user_id=actor_staff_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_data=before_data,
                after_data=after_data,
            )
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            return log_entry
