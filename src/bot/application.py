import logging

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    filters,
)

from src.bot.handlers.commands import help_command, performance_command, quiz_command
from src.bot.handlers.home import handle_home_callback
from src.bot.handlers.profile_setup import handle_profile_setup_callback
from src.bot.handlers.reporting import handle_report_callback, handle_report_note_message
from src.bot.handlers.quiz import handle_poll_answer
from src.bot.handlers.start import start_command
from src.bot.runtime_config import BOT_CONFIG_KEY, BotRuntimeConfig
from src.config import BOT_CONFIGS, DEFAULT_BOT_CONFIG
from src.domains.catalog.navigation_service import CatalogNavigationService
from src.domains.home.service import HomeService
from src.domains.performance.service import PerformanceService
from src.domains.profile.service import ProfileService
from src.domains.quiz_entry.service import QuizEntryService
from src.domains.quiz.service import QuizSessionService

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


async def handle_application_error(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    logger.exception(
        "Unhandled Telegram application error.",
        exc_info=context.error,
    )

    if not isinstance(update, Update):
        return

    if update.callback_query:
        try:
            await update.callback_query.answer(
                "Something went wrong. Please try again.",
                show_alert=True,
            )
        except Exception:
            logger.exception("Failed to answer callback query after bot error.")
        return

    if update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Something went wrong on our side. Please try again in a moment."
            )
        except Exception:
            logger.exception("Failed to send fallback error message to Telegram user.")


def get_application(
    bot_config: BotRuntimeConfig | None = None,
) -> Application:
    """Create and configure the Telegram application."""
    bot_config = bot_config or DEFAULT_BOT_CONFIG
    application = Application.builder().token(bot_config.telegram_bot_token).build()
    application.bot_data[BOT_CONFIG_KEY] = bot_config
    application.bot_data["catalog_service"] = CatalogNavigationService()
    application.bot_data["profile_service"] = ProfileService()
    application.bot_data["home_service"] = HomeService()
    application.bot_data["performance_service"] = PerformanceService()
    application.bot_data["quiz_entry_service"] = QuizEntryService()
    application.bot_data["quiz_session_service"] = QuizSessionService()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("performance", performance_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(
        CallbackQueryHandler(handle_profile_setup_callback, pattern=r"^profile:")
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_home_callback,
            pattern=r"^(home:|quiz:course:|quiz:length:)",
        )
    )
    application.add_handler(
        CallbackQueryHandler(handle_report_callback, pattern=r"^report:")
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_note_message)
    )
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    application.add_error_handler(handle_application_error)
    return application


def get_telegram_applications(
    bot_configs: dict[str, BotRuntimeConfig] | None = None,
) -> dict[str, Application]:
    return {
        bot_id: get_application(bot_config)
        for bot_id, bot_config in (bot_configs or BOT_CONFIGS).items()
    }


telegram_app = get_application()
