from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.api.admin_auth import require_admin_permission
from src.domains.admin.question_service import AdminQuestionService


router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])


def get_admin_question_service(_request: Request) -> AdminQuestionService:
    return AdminQuestionService()


@router.get("")
async def list_questions(
    request: Request,
    course_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _principal=Depends(require_admin_permission("questions.view")),
):
    service = get_admin_question_service(request)
    items = await service.list_questions(
        course_id=course_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "count": len(items)}


@router.patch("/{question_key}")
async def update_question(
    question_key: str,
    request: Request,
    principal=Depends(require_admin_permission("questions.edit")),
):
    service = get_admin_question_service(request)
    payload = await request.json()
    updated = await service.update_question(
        question_key,
        payload,
        actor_staff_user_id=principal.staff_user_id,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )
    return updated
