import logging


logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, repository):
        self.repository = repository

    async def track_event(
        self,
        user_id: int,
        event_type: str,
        metadata: dict | None = None,
        *,
        bot_id: str | None = None,
    ):
        payload = metadata or {}
        logger.info(
            "[ANALYTICS] user_id=%s event_type=%s bot_id=%s metadata=%s",
            user_id,
            event_type,
            bot_id,
            payload,
        )
        return await self.repository.create_event(
            user_id=user_id,
            event_type=event_type,
            metadata=payload,
            bot_id=bot_id,
        )
