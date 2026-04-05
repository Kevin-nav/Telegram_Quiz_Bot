from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.api.admin_auth import require_admin_permission
from src.domains.admin.auth_service import AdminPrincipal
from src.domains.admin.report_service import AdminReportService, VALID_REPORT_STATUSES
from src.domains.admin.scope_service import AdminScopeService


router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


def get_admin_report_service(_request: Request) -> AdminReportService:
    return AdminReportService()


def get_admin_scope_service(_request: Request) -> AdminScopeService:
    return AdminScopeService()


@router.get("")
async def list_reports(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    principal: AdminPrincipal = Depends(require_admin_permission("audit.view")),
):
    if status_filter and status_filter not in VALID_REPORT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report status.",
        )

    scope_service = get_admin_scope_service(request)
    active_bot_id = scope_service.resolve_active_bot_id(principal)
    course_codes = await scope_service.resolve_course_codes_for_principal(principal)
    service = get_admin_report_service(request)
    return await service.list_reports(
        active_bot_id=active_bot_id,
        course_codes=course_codes,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("audit.view")),
):
    scope_service = get_admin_scope_service(request)
    active_bot_id = scope_service.resolve_active_bot_id(principal)
    course_codes = await scope_service.resolve_course_codes_for_principal(principal)
    service = get_admin_report_service(request)
    payload = await service.get_report(
        report_id,
        active_bot_id=active_bot_id,
        course_codes=course_codes,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question report not found.",
        )
    return payload


@router.patch("/{report_id}/status")
async def update_report_status(
    report_id: int,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("questions.edit")),
):
    payload = await request.json()
    next_status = str(payload.get("status") or "").strip().lower()
    if next_status not in VALID_REPORT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report status.",
        )

    scope_service = get_admin_scope_service(request)
    active_bot_id = scope_service.resolve_active_bot_id(principal)
    course_codes = await scope_service.resolve_course_codes_for_principal(principal)
    service = get_admin_report_service(request)
    updated = await service.update_report_status(
        report_id,
        status=next_status,
        actor_staff_user_id=principal.staff_user_id,
        active_bot_id=active_bot_id,
        course_codes=course_codes,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question report not found.",
        )
    return updated
