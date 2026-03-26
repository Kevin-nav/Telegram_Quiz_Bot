def test_app_import():
    from src.main import app

    assert app is not None


def test_home_callback_handler_accepts_quiz_course_callbacks():
    from src.bot.application import telegram_app

    callback_handlers = [
        handler
        for handlers in telegram_app.handlers.values()
        for handler in handlers
        if handler.__class__.__name__ == "CallbackQueryHandler"
    ]

    assert any(
        handler.pattern is not None
        and handler.pattern.pattern == r"^(home:|quiz:course:|quiz:length:)"
        for handler in callback_handlers
    )
