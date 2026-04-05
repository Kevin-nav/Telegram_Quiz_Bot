from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.bootstrap import create_app_state, shutdown_web_app, startup_web_app
from src.api.admin_audit import router as admin_audit_router
from src.api.admin_analytics import router as admin_analytics_router
from src.api.admin_auth import router as admin_auth_router
from src.api.admin_catalog import router as admin_catalog_router
from src.api.admin_questions import router as admin_questions_router
from src.api.admin_reports import router as admin_reports_router
from src.api.admin_staff import router as admin_staff_router
from src.api.health import router as health_router
from src.api.webhooks import router as webhook_router
from src.core.config import settings

import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = await create_app_state()
    app.state.runtime = runtime
    await startup_web_app(runtime)

    yield

    await shutdown_web_app(runtime)


app = FastAPI(lifespan=lifespan)
app.state.runtime = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_admin_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(admin_auth_router)
app.include_router(admin_staff_router)
app.include_router(admin_catalog_router)
app.include_router(admin_questions_router)
app.include_router(admin_audit_router)
app.include_router(admin_analytics_router)
app.include_router(admin_reports_router)
app.include_router(webhook_router)
app.include_router(health_router)


if __name__ == "__main__":
    import uvicorn

    # This allows running `python src/main.py` directly for local testing
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
