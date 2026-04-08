from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.api.admin_auth import get_permission_service, require_admin_permission
from src.domains.admin.auth_service import AdminPrincipal
from src.domains.admin.question_service import AdminQuestionService
from src.domains.admin.scope_service import AdminScopeService


router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])


def get_admin_question_service(_request: Request) -> AdminQuestionService:
    return AdminQuestionService()


def get_admin_scope_service(_request: Request) -> AdminScopeService:
    return AdminScopeService()


@router.get("")
async def list_questions(
    request: Request,
    course_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    principal: AdminPrincipal = Depends(require_admin_permission("questions.view")),
):
    scope_service = get_admin_scope_service(request)
    course_codes = await scope_service.resolve_course_codes_for_principal(principal)
    service = get_admin_question_service(request)
    items = await service.list_questions(
        course_id=course_id,
        status=status_filter,
        course_codes=course_codes,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "count": len(items)}


@router.patch("/{question_key}")
async def update_question(
    question_key: str,
    request: Request,
    principal: AdminPrincipal = Depends(require_admin_permission("questions.edit")),
):
    service = get_admin_question_service(request)
    payload = await request.json()
    bot_id = getattr(principal, "active_bot_id", None)
    if bot_id:
        existing = await service.question_repository.get_question(question_key)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found.",
            )
        permission_service = get_permission_service(request)
        allowed = await permission_service.user_can_access_bot_catalog_scope(
            principal.staff_user_id,
            bot_id,
            course_code=existing.course_id,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This admin user cannot edit questions in this course scope.",
            )
    updated = await service.update_question(
        question_key,
        payload,
        actor_staff_user_id=principal.staff_user_id,
        active_bot_id=bot_id,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )
    return updated
