from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.app.bootstrap import create_app_state, shutdown_web_app, startup_web_app
from src.api.health import router as health_router
from src.api.webhooks import router as webhook_router

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
app.include_router(webhook_router)
app.include_router(health_router)


if __name__ == "__main__":
    import uvicorn

    # This allows running `python src/main.py` directly for local testing
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
