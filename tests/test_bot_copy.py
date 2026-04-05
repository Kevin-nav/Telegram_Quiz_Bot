from src.bot.copy import (
    build_help_message,
    build_home_message,
    build_welcome_message,
)
from src.bot.runtime_config import DEFAULT_BOT_THEMES


def test_home_copy_mentions_profile_details():
    message = build_home_message(
        {
            "faculty_name": "Faculty of Engineering",
            "program_name": "Mechanical Engineering",
            "level_name": "Level 100",
        }
    )

    assert "Faculty of Engineering" in message
    assert "Mechanical Engineering" in message
    assert "Level 100" in message


def test_welcome_copy_is_short_and_guiding():
    message = build_welcome_message("Kevin")

    assert message.startswith("Welcome, Kevin.")
    assert "study profile" in message.lower()


def test_help_copy_mentions_primary_actions():
    message = build_help_message()

    assert "Start Quiz" in message
    assert "Change Course" in message


def test_help_copy_uses_bot_specific_home_labels():
    message = build_help_message(DEFAULT_BOT_THEMES["adarkwa"])

    assert "Start Practice" in message
    assert "Study Setup" in message
