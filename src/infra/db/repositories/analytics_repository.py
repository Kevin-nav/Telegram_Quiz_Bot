from src.infra.db.models.analytics_event import AnalyticsEvent
from src.infra.db.session import AsyncSessionLocal


class AnalyticsRepository:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def create_event(self, user_id: int, event_type: str, metadata: dict | None = None):
        payload = metadata or {}

        async with self.session_factory() as session:
            event = AnalyticsEvent(
                user_id=user_id,
                event_type=event_type,
                event_metadata=payload,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event
