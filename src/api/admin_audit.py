from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.admin_auth import require_admin_permission


router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


@router.get("")
async def list_audit_logs(
    _principal=Depends(require_admin_permission("audit.view")),
):
    return {"items": [], "count": 0}
