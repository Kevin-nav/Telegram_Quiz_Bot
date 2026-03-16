from types import SimpleNamespace

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.cache import redis_client
from src.core.config import get_settings
from src.database import engine


router = APIRouter()


def get_runtime(request: Request):
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is not None:
        return runtime

    return SimpleNamespace(
        settings=get_settings(),
        redis=redis_client,
        db_engine=engine,
    )


async def check_readiness(runtime) -> dict[str, str]:
    status_map = {"redis": "ok", "database": "ok"}

    try:
        await runtime.redis.ping()
    except Exception:
        status_map["redis"] = "error"

    try:
        async with runtime.db_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        status_map["database"] = "error"

    return status_map


@router.get("/health")
@router.get("/health/live")
async def health_live():
    return {"status": "ok", "message": "Adarkwa Study Bot is running."}


@router.get("/health/ready")
async def health_ready(request: Request):
    runtime = get_runtime(request)
    checks = await check_readiness(runtime)
    is_ready = all(value == "ok" for value in checks.values())
    payload = {"status": "ok" if is_ready else "degraded", "checks": checks}
    response_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=response_code, content=payload)
