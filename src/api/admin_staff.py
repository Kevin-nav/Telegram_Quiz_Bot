from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.admin_auth import require_admin_permission
from src.domains.admin.auth_service import AdminPrincipal
from src.domains.admin.staff_service import AdminStaffService


router = APIRouter(prefix="/admin/staff", tags=["admin-staff"])


def get_admin_staff_service(_request: Request) -> AdminStaffService:
    return AdminStaffService()


@router.get("")
async def list_staff_users(
    request: Request,
    _principal: AdminPrincipal = Depends(require_admin_permission("staff.view")),
):
    service = get_admin_staff_service(request)
    items = await service.list_staff_users()
    return {"items": items, "count": len(items)}


@router.get("/{staff_user_id}")
async def read_staff_user(
    staff_user_id: int,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("staff.view")),
):
    service = get_admin_staff_service(request)
    target = await service.get_staff_user(staff_user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found.",
        )

    payload = dict(target)
    payload["requested_by"] = principal.staff_user_id
    return payload


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_staff_user(
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("staff.create")),
):
    service = get_admin_staff_service(request)
    payload = await request.json()
    try:
        return await service.create_staff_user(
            payload,
            actor_staff_user_id=principal.staff_user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/{staff_user_id}")
async def update_staff_user(
    staff_user_id: int,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("staff.edit_permissions")),
):
    service = get_admin_staff_service(request)
    payload = await request.json()
    try:
        updated = await service.update_staff_user(
            staff_user_id,
            payload,
            actor_staff_user_id=principal.staff_user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found.",
        )
    return updated


@router.post("/{staff_user_id}/reset-password")
async def reset_staff_password(
    staff_user_id: int,
    request: Request,
    principal: AdminPrincipal = Depends(
        require_admin_permission("staff.edit_permissions")
    ),
):
    service = get_admin_staff_service(request)
    payload = await request.json()
    try:
        updated = await service.reset_staff_password(
            staff_user_id,
            str(payload.get("temporary_password") or ""),
            actor_staff_user_id=principal.staff_user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff user not found.",
        )
    return updated
