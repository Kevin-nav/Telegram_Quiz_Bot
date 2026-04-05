import pytest

from src.domains.analytics.service import AnalyticsService


class FakeAnalyticsRepository:
    def __init__(self):
        self.calls = []

    async def create_event(
        self,
        user_id: int,
        event_type: str,
        metadata: dict,
        *,
        bot_id: str | None = None,
    ):
        payload = {
            "user_id": user_id,
            "event_type": event_type,
            "metadata": metadata,
            "bot_id": bot_id,
        }
        self.calls.append(payload)
        return payload


@pytest.mark.asyncio
async def test_track_event_persists_via_repository():
    repository = FakeAnalyticsRepository()
    service = AnalyticsService(repository)

    result = await service.track_event(
        user_id=42,
        event_type="User Registered",
        metadata={"source": "telegram"},
        bot_id="adarkwa",
    )

    assert repository.calls == [result]
    assert result["bot_id"] == "adarkwa"
    assert result["metadata"]["source"] == "telegram"
