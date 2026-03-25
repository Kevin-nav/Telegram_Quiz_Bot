from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from src.api.admin_auth import require_admin_permission
from src.domains.admin.audit_service import AdminAuditService


router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


def get_admin_audit_service(_request: Request) -> AdminAuditService:
    return AdminAuditService()


@router.get("")
async def list_audit_logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _principal=Depends(require_admin_permission("audit.view")),
):
    service = get_admin_audit_service(request)
    items = await service.list_audit_logs(limit=limit, offset=offset)
    return {"items": items, "count": len(items)}
