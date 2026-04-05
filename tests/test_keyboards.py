from src.bot.callbacks import (
    profile_course_callback,
    quiz_course_callback,
    report_reason_callback,
    report_start_callback,
)
from src.bot.keyboards import (
    build_answer_action_keyboard,
    build_question_action_keyboard,
    build_report_reason_keyboard,
    build_quiz_course_keyboard,
    build_quiz_length_keyboard,
    build_welcome_keyboard,
)
from src.bot.runtime_config import DEFAULT_BOT_THEMES


def test_profile_course_callback_is_namespaced():
    assert profile_course_callback("calc-101") == "profile:course:calc-101"


def test_quiz_course_callback_is_namespaced():
    assert quiz_course_callback("linear-electronics") == "quiz:course:linear-electronics"


def test_report_callbacks_are_namespaced():
    assert report_start_callback("question") == "report:start:question"
    assert (
        report_reason_callback("answer", "correct_answer_shown_is_wrong")
        == "report:reason:answer:correct_answer_shown_is_wrong"
    )


def test_welcome_keyboard_has_setup_button():
    keyboard = build_welcome_keyboard()

    assert keyboard.inline_keyboard[0][0].text == "Set Up Study Profile"
    assert keyboard.inline_keyboard[0][0].callback_data == "profile:start:setup"


def test_welcome_keyboard_uses_bot_specific_labels():
    keyboard = build_welcome_keyboard(DEFAULT_BOT_THEMES["adarkwa"])

    assert keyboard.inline_keyboard[0][0].text == "Study Setup"
    assert keyboard.inline_keyboard[1][0].text == "Help"


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


def test_question_action_keyboard_has_report_button():
    keyboard = build_question_action_keyboard()

    assert keyboard.inline_keyboard[0][0].text == "Report Question"
    assert keyboard.inline_keyboard[0][0].callback_data == "report:start:question"


def test_answer_action_keyboard_has_answer_report_button():
    keyboard = build_answer_action_keyboard()

    assert keyboard.inline_keyboard[0][0].text == "Not correct? Report"
    assert keyboard.inline_keyboard[0][0].callback_data == "report:start:answer"


def test_report_reason_keyboard_uses_scope_specific_reason_callbacks():
    keyboard = build_report_reason_keyboard(
        "question",
        [
            ("Question unclear", "question_unclear"),
            ("Other", "other"),
        ],
    )

    assert [row[0].callback_data for row in keyboard.inline_keyboard[:-1]] == [
        "report:reason:question:question_unclear",
        "report:reason:question:other",
    ]
    assert keyboard.inline_keyboard[-1][0].callback_data == "report:cancel:question"
