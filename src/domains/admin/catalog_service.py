from __future__ import annotations

from src.cache import redis_client
from src.domains.catalog.service import CatalogService
from src.infra.db.repositories.audit_log_repository import AuditLogRepository
from src.infra.db.repositories.catalog_repository import CatalogRepository
from src.infra.redis.state_store import InteractiveStateStore


class AdminCatalogService:
    def __init__(
        self,
        catalog_repository: CatalogRepository | None = None,
        state_store: InteractiveStateStore | None = None,
        audit_log_repository: AuditLogRepository | None = None,
        read_service: CatalogService | None = None,
    ):
        self.catalog_repository = catalog_repository or CatalogRepository()
        self.state_store = state_store or InteractiveStateStore(redis_client)
        self.audit_log_repository = audit_log_repository or AuditLogRepository()
        self.read_service = read_service or CatalogService(
            repository=self.catalog_repository,
            state_store=self.state_store,
        )

    async def list_offerings(self, **filters) -> list[dict]:
        offerings = await self.catalog_repository.list_offerings(**filters)
        return [self._serialize_offering(offering) for offering in offerings]

    async def upsert_offering(
        self,
        payload: dict,
        *,
        actor_staff_user_id: int | None = None,
    ) -> dict:
        normalized = self._normalize_offering_payload(payload)
        before = await self._find_existing_offering(normalized)
        offering = await self.catalog_repository.upsert_offering(normalized)
        await self.state_store.invalidate_catalog_cache()
        after = self._serialize_offering(offering)
        await self.audit_log_repository.create_audit_log(
            action="catalog.offering.updated",
            entity_type="program_course_offerings",
            entity_id=str(offering.id),
            actor_staff_user_id=actor_staff_user_id,
            before_data=before,
            after_data=after,
        )
        return after

    async def _find_existing_offering(self, payload: dict) -> dict | None:
        offerings = await self.catalog_repository.list_offerings(
            program_code=payload["program_code"],
            level_code=payload["level_code"],
            semester_code=payload["semester_code"],
        )
        for offering in offerings:
            if offering.course_code == payload["course_code"]:
                return self._serialize_offering(offering)
        return None

    def _normalize_offering_payload(self, payload: dict) -> dict:
        normalized = {
            "program_code": str(payload["program_code"]).strip(),
            "level_code": str(payload["level_code"]).strip(),
            "semester_code": str(payload["semester_code"]).strip(),
            "course_code": str(payload["course_code"]).strip(),
            "is_active": bool(payload.get("is_active", True)),
        }
        return normalized

    def _serialize_offering(self, offering) -> dict:
        return {
            "id": offering.id,
            "program_code": offering.program_code,
            "level_code": offering.level_code,
            "semester_code": offering.semester_code,
            "course_code": offering.course_code,
            "is_active": bool(getattr(offering, "is_active", True)),
        }
