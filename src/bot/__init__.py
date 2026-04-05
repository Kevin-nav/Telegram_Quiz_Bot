"""Telegram bot application package."""

from importlib import import_module

__all__ = ["get_application", "set_bot_commands", "telegram_app"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    application_module = import_module("src.bot.application")
    return getattr(application_module, name)
