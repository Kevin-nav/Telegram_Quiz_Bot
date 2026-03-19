from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import DATABASE_CONNECT_ARGS, DATABASE_URL
from src.infra.db.base import Base


if not DATABASE_URL:
    raise ValueError("No DATABASE_URL set for the database connection")


engine = create_async_engine(
    DATABASE_URL,
    connect_args=DATABASE_CONNECT_ARGS,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


__all__ = ["AsyncSessionLocal", "Base", "engine", "get_db"]
