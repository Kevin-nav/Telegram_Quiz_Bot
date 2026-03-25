from __future__ import annotations

import src.api.admin_auth as admin_auth
from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.admin_auth import principal_payload, require_admin_permission
from src.domains.admin.auth_service import AdminPrincipal


router = APIRouter(prefix="/admin/staff", tags=["admin-staff"])


@router.get("/{staff_user_id}")
async def read_staff_user(
    staff_user_id: int,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("staff.view")),
):
    auth_service = admin_auth.get_auth_service(request)
    target = await auth_service.get_principal(staff_user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found.",
        )

    payload = principal_payload(target)
    payload["requested_by"] = principal.staff_user_id
    return payload
