import pytest
import os

# Set environment variables for testing before importing anything
os.environ["APP_ENV"] = "testing"
os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["WEBHOOK_SECRET"] = "test-secret"
os.environ["WEBHOOK_URL"] = "http://testserver/webhook"

from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def async_client():
    # Use httpx AsyncClient to test FastAPI app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
