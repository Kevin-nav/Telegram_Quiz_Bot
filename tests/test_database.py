import pytest
from src.database import get_db


@pytest.mark.asyncio
async def test_database_connection():
    """Test that we can get a database session without errors."""
    try:
        # Simply testing the generator yields a session
        async for session in get_db():
            assert session is not None
            break
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")
