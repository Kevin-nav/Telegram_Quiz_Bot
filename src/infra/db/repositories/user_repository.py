from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from src.infra.db.models.user import User
from src.infra.db.session import AsyncSessionLocal


class UserRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def get_by_id(self, user_id: int) -> User | None:
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    async def touch_activity(self, user_id: int, *, occurred_at) -> User | None:
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return None

            user.last_active_at = occurred_at
            activity_date = occurred_at.date()
            last_active_date = getattr(user, "last_active_date", None)
            if last_active_date == activity_date:
                pass
            elif last_active_date == activity_date - timedelta(days=1):
                user.current_streak = int(getattr(user, "current_streak", 0) or 0) + 1
            else:
                user.current_streak = 1
            user.longest_streak = max(
                int(getattr(user, "longest_streak", 0) or 0),
                int(getattr(user, "current_streak", 0) or 0),
            )
            user.last_active_date = activity_date

            await session.commit()
            await session.refresh(user)
            return user
