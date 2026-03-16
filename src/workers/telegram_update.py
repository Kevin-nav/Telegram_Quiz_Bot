import logging

from telegram import Update


logger = logging.getLogger(__name__)


async def process_telegram_update(runtime, payload: dict) -> None:
    update_id = payload.get("update_id")
    logger.info("Processing Telegram update %s.", update_id)

    update = Update.de_json(payload, runtime.telegram_app.bot)
    await runtime.telegram_app.process_update(update)
