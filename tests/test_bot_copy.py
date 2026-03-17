from src.bot.copy import (
    build_help_message,
    build_home_message,
    build_welcome_message,
)


def test_home_copy_mentions_current_course():
    message = build_home_message(
        {
            "faculty_name": "Faculty of Engineering",
            "program_name": "Mechanical Engineering",
            "level_name": "Level 100",
            "semester_name": "First Semester",
            "course_name": "Calculus",
        }
    )

    assert "Semester: First Semester" in message
    assert "Course: Calculus" in message


def test_welcome_copy_is_short_and_guiding():
    message = build_welcome_message("Kevin")

    assert message.startswith("Welcome, Kevin.")
    assert "study profile" in message.lower()


def test_help_copy_mentions_primary_actions():
    message = build_help_message()

    assert "Start Quiz" in message
    assert "Change Course" in message
