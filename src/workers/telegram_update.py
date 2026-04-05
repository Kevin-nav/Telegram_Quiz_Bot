import logging

from telegram import Update

from src.bot.runtime_config import TANJAH_BOT_ID

logger = logging.getLogger(__name__)


async def process_telegram_update(
    runtime,
    payload: dict,
    *,
    bot_id: str = TANJAH_BOT_ID,
) -> None:
    bot_id, update_payload = _unwrap_update_payload(payload, bot_id=bot_id)
    telegram_app = _resolve_telegram_app(runtime, bot_id)

    update_id = update_payload.get("update_id")
    logger.info("Processing Telegram update %s.", update_id)

    update = Update.de_json(update_payload, telegram_app.bot)
    await telegram_app.process_update(update)


def _unwrap_update_payload(
    payload: dict,
    *,
    bot_id: str,
) -> tuple[str, dict]:
    nested_payload = payload.get("payload")
    if isinstance(nested_payload, dict):
        return payload.get("bot_id") or bot_id, nested_payload
    return payload.get("bot_id") or bot_id, payload


def _resolve_telegram_app(runtime, bot_id: str):
    telegram_apps = getattr(runtime, "telegram_apps", None)
    if isinstance(telegram_apps, dict):
        return telegram_apps.get(bot_id) or runtime.telegram_app
    return runtime.telegram_app
