import logging

from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from src.config import TELEGRAM_BOT_TOKEN
from src.bot.handlers.profile_setup import handle_profile_setup_callback
from src.bot.handlers.start import start_command
from src.domains.catalog.navigation_service import CatalogNavigationService
from src.domains.home.service import HomeService
from src.domains.profile.service import ProfileService

logger = logging.getLogger(__name__)


async def set_bot_commands(application: Application) -> None:
    """Sets the bot's commands available in the Telegram menu."""
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Start the bot"),
            BotCommand("quiz", "Start a new quiz session"),
            BotCommand("performance", "See your quiz performance"),
            BotCommand("help", "Show help information"),
        ]
    )


def get_application() -> Application:
    """Create and configure the Telegram application."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.bot_data["catalog_service"] = CatalogNavigationService()
    application.bot_data["profile_service"] = ProfileService()
    application.bot_data["home_service"] = HomeService()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_profile_setup_callback, pattern=r"^profile:"))
    return application


telegram_app = get_application()
