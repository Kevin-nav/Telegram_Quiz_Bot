from __future__ import annotations

from dataclasses import asdict, is_dataclass

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from src.domains.admin.auth_service import AdminPrincipal, AuthService
from src.domains.admin.permission_service import PermissionService


router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def get_auth_service(_request: Request) -> AuthService:
    return AuthService()


def get_permission_service(_request: Request) -> PermissionService:
    return PermissionService()


async def get_admin_principal(
    request: Request,
    x_admin_user_id: str | None = Header(default=None, alias="X-Admin-User-Id"),
) -> AdminPrincipal:
    if not x_admin_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin credentials.",
        )

    try:
        staff_user_id = int(x_admin_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        ) from exc

    auth_service = get_auth_service(request)
    principal = await auth_service.get_principal(staff_user_id)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )
    return principal


def require_admin_permission(permission_code: str):
    async def dependency(
        request: Request,
        x_admin_user_id: str | None = Header(default=None, alias="X-Admin-User-Id"),
    ) -> AdminPrincipal:
        principal = await get_admin_principal(request, x_admin_user_id)
        permission_service = get_permission_service(request)
        allowed = await permission_service.user_has_permission(
            principal.staff_user_id,
            permission_code,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient admin permissions.",
            )
        return principal

    return dependency


def principal_payload(principal: AdminPrincipal) -> dict:
    if is_dataclass(principal):
        return asdict(principal)
    return dict(vars(principal))


@router.get("/me")
async def admin_me(principal: AdminPrincipal = Depends(get_admin_principal)):
    return principal_payload(principal)
