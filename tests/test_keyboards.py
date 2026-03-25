from src.bot.callbacks import profile_course_callback, quiz_course_callback
from src.bot.keyboards import (
    build_quiz_course_keyboard,
    build_quiz_length_keyboard,
    build_welcome_keyboard,
)


def test_profile_course_callback_is_namespaced():
    assert profile_course_callback("calc-101") == "profile:course:calc-101"


def test_quiz_course_callback_is_namespaced():
    assert quiz_course_callback("linear-electronics") == "quiz:course:linear-electronics"


def test_welcome_keyboard_has_setup_button():
    keyboard = build_welcome_keyboard()

    assert keyboard.inline_keyboard[0][0].text == "Set Up Study Profile"
    assert keyboard.inline_keyboard[0][0].callback_data == "profile:start:setup"


def test_quiz_length_keyboard_uses_namespaced_callbacks():
    keyboard = build_quiz_length_keyboard()

    callbacks = [row[0].callback_data for row in keyboard.inline_keyboard]
    assert callbacks == ["quiz:length:10", "quiz:length:20", "quiz:length:30"]


def test_quiz_course_keyboard_lists_courses_and_back_action():
    keyboard = build_quiz_course_keyboard(
        [
            {"code": "linear-electronics", "name": "Linear Electronics"},
            {"code": "thermodynamics", "name": "Thermodynamics"},
        ]
    )

    assert [row[0].text for row in keyboard.inline_keyboard[:-1]] == [
        "Linear Electronics",
        "Thermodynamics",
    ]
    assert [row[0].callback_data for row in keyboard.inline_keyboard[:-1]] == [
        "quiz:course:linear-electronics",
        "quiz:course:thermodynamics",
    ]
    assert keyboard.inline_keyboard[-1][0].text == "Back"
    assert keyboard.inline_keyboard[-1][0].callback_data == "home:start_quiz"
