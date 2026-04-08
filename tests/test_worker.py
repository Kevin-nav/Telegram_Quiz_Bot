import pytest
from unittest.mock import AsyncMock, patch
from src.tasks.worker import WorkerSettings, precompute_admin_analytics, process_telegram_update


@pytest.mark.asyncio
async def test_process_telegram_update():
    """Test that the worker can successfully process an update payload."""

    payload = {
        "update_id": 10000,
        "message": {
            "message_id": 1,
            "date": 1441645532,
            "chat": {"id": 1111111, "type": "private"},
            "text": "/start",
        },
    }

    mock_app = AsyncMock()
    mock_app.bot = "mock_bot"
    runtime = type("Runtime", (), {"telegram_app": mock_app})()

    with patch("src.workers.telegram_update.Update.de_json") as mock_de_json:
        mock_de_json.return_value = "mock_update"
        await process_telegram_update({"runtime": runtime}, payload)

        mock_de_json.assert_called_once_with(payload, "mock_bot")
        mock_app.process_update.assert_called_once_with("mock_update")


def test_worker_registers_question_report_job():
    function_names = {function.__name__ for function in WorkerSettings.functions}

    assert "persist_question_report" in function_names
    assert "precompute_admin_analytics" in function_names


@pytest.mark.asyncio
async def test_precompute_admin_analytics_forwards_payload_to_background_job():
    with patch(
        "src.tasks.worker.handle_precompute_admin_analytics",
        new=AsyncMock(),
    ) as handler:
        await precompute_admin_analytics({}, {"bot_id": "adarkwa", "course_codes": ["signals"]})

    handler.assert_awaited_once_with({"bot_id": "adarkwa", "course_codes": ["signals"]})
