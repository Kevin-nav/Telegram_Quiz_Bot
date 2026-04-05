from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.admin_auth import require_admin_permission
from src.domains.admin.analytics_service import AdminAnalyticsService
from src.domains.admin.auth_service import AdminPrincipal
from src.domains.admin.scope_service import AdminScopeService


router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


def get_admin_analytics_service(_request: Request) -> AdminAnalyticsService:
    return AdminAnalyticsService()


def get_admin_scope_service(_request: Request) -> AdminScopeService:
    return AdminScopeService()


@router.get("")
async def get_analytics_summary(
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("analytics.view")),
):
    scope_service = get_admin_scope_service(request)
    active_bot_id = scope_service.resolve_active_bot_id(principal)
    course_codes = await scope_service.resolve_course_codes_for_principal(principal)
    service = get_admin_analytics_service(request)
    return await service.get_summary(
        active_bot_id=active_bot_id,
        course_codes=course_codes,
    )


@router.get("/students/{user_id}")
async def get_student_analytics_detail(
    user_id: int,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("analytics.view")),
):
    scope_service = get_admin_scope_service(request)
    active_bot_id = scope_service.resolve_active_bot_id(principal)
    course_codes = await scope_service.resolve_course_codes_for_principal(principal)
    service = get_admin_analytics_service(request)
    payload = await service.get_student_detail(
        user_id,
        active_bot_id=active_bot_id,
        course_codes=course_codes,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student analytics record not found.",
        )
    return payload
