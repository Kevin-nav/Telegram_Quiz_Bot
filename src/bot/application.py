import logging

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.analytics.internal_analytics import analytics
from src.config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user

    await analytics.track_event(
        user_id=user.id,
        event_type="User Registered",
        metadata={"username": user.username, "first_name": user.first_name},
    )

    from src.config import WELCOME_MESSAGE

    await update.message.reply_text(WELCOME_MESSAGE)


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
    application.add_handler(CommandHandler("start", start))
    return application


telegram_app = get_application()
