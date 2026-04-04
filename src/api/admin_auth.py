from __future__ import annotations

from dataclasses import asdict, is_dataclass

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from src.domains.admin.auth_service import AdminPrincipal, AuthService
from src.domains.admin.permission_service import PermissionService
from src.core.config import settings


router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])
ADMIN_SESSION_COOKIE_NAME = "admin_session"


def get_auth_service(_request: Request) -> AuthService:
    return AuthService()


def get_permission_service(_request: Request) -> PermissionService:
    return PermissionService()


async def get_admin_principal(
    request: Request,
) -> AdminPrincipal:
    session_token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin credentials.",
        )

    auth_service = get_auth_service(request)
    principal = await auth_service.get_principal_for_session_token(session_token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )
    return principal


def require_admin_permission(permission_code: str):
    async def dependency(
        request: Request,
    ) -> AdminPrincipal:
        principal = await get_admin_principal(request)
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


@router.post("/login")
async def admin_login(request: Request, response: Response):
    payload = await request.json()
    email = str(payload.get("email") or "").strip()
    password = str(payload.get("password") or "")
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required.",
        )

    auth_service = get_auth_service(request)
    login_result = await auth_service.login(
        email,
        password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    if login_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    principal, session_token = login_result
    response.set_cookie(
        ADMIN_SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env not in {"development", "test", "local"},
        domain=settings.admin_session_cookie_domain,
        max_age=12 * 60 * 60,
        path="/",
    )
    return principal_payload(principal)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def admin_logout(
    request: Request,
    response: Response,
    _principal: AdminPrincipal = Depends(get_admin_principal),
):
    session_token = request.cookies.get(ADMIN_SESSION_COOKIE_NAME)
    if session_token:
        auth_service = get_auth_service(request)
        await auth_service.logout(session_token)
    response.delete_cookie(
        ADMIN_SESSION_COOKIE_NAME,
        domain=settings.admin_session_cookie_domain,
        path="/",
    )
    return None


@router.post("/set-password")
async def admin_set_password(
    request: Request,
    principal: AdminPrincipal = Depends(get_admin_principal),
):
    payload = await request.json()
    current_password = str(payload.get("current_password") or "")
    new_password = str(payload.get("new_password") or "")
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters.",
        )

    auth_service = get_auth_service(request)
    updated_principal = await auth_service.set_password(
        principal.staff_user_id,
        current_password=current_password,
        new_password=new_password,
    )
    if updated_principal is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is invalid.",
        )
    return principal_payload(updated_principal)


@router.post("/select-bot")
async def admin_select_bot(
    request: Request,
    principal: AdminPrincipal = Depends(get_admin_principal),
):
    payload = await request.json()
    bot_id = str(payload.get("bot_id") or "").strip()
    if not bot_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bot_id is required.",
        )

    auth_service = get_auth_service(request)
    updated_principal = await auth_service.set_active_bot(
        principal.staff_user_id,
        bot_id,
    )
    if updated_principal is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bot workspace is not available to this admin user.",
        )
    return principal_payload(updated_principal)
