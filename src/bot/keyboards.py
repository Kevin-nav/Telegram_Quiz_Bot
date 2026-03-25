from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.callbacks import (
    home_callback,
    profile_back_callback,
    profile_callback,
    profile_cancel_callback,
    quiz_course_callback,
    quiz_length_callback,
)


def _button(label: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(label, callback_data=callback_data)


def build_welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [_button("Set Up Study Profile", profile_callback("start", "setup"))],
            [_button("Help", home_callback("help"))],
        ]
    )


def build_setup_keyboard(
    section: str,
    options: list[dict[str, str]],
    *,
    include_back: bool = True,
    include_cancel: bool = True,
) -> InlineKeyboardMarkup:
    rows = [[_button(option["name"], profile_callback(section, option["code"]))] for option in options]

    nav_row = []
    if include_back:
        nav_row.append(_button("Back", profile_back_callback()))
    if include_cancel:
        nav_row.append(_button("Cancel", profile_cancel_callback()))
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(rows)


def build_home_keyboard(buttons: list[list[dict[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [_button(button["label"], button["callback"]) for button in row]
            for row in buttons
        ]
    )


def build_quiz_length_keyboard(lengths: tuple[int, ...] = (10, 20, 30)) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[_button(f"{length} Questions", quiz_length_callback(length))] for length in lengths]
    )


def build_quiz_course_keyboard(
    courses: list[dict[str, str]],
    *,
    include_back: bool = True,
) -> InlineKeyboardMarkup:
    rows = [
        [_button(course["name"], quiz_course_callback(course["code"]))]
        for course in courses
    ]

    if include_back:
        rows.append([_button("Back", home_callback("start_quiz"))])

    return InlineKeyboardMarkup(rows)
