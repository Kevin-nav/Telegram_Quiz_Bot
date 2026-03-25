from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.admin_auth import require_admin_permission


router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])


@router.get("")
async def list_questions(
    _principal=Depends(require_admin_permission("questions.view")),
):
    return {"items": [], "count": 0}
