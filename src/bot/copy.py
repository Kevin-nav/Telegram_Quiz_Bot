from collections.abc import Mapping

from src.bot.runtime_config import BotThemeConfig


def _button_label(
    key: str,
    fallback: str,
    bot_theme: BotThemeConfig | None = None,
) -> str:
    if bot_theme is None:
        return fallback
    return bot_theme.button_labels.get(key) or fallback


def build_welcome_message(
    first_name: str | None,
    bot_theme: BotThemeConfig | None = None,
) -> str:
    learner_name = first_name or "student"
    if bot_theme and bot_theme.welcome_message_template:
        return bot_theme.welcome_message_template.format(
            brand_name=bot_theme.brand_name,
            learner_name=learner_name
        )

    prefix = "Welcome"
    if bot_theme is not None:
        prefix = f"Welcome to {bot_theme.brand_name}"
    return (
        f"{prefix}, {learner_name}.\n\n"
        "Set up your study profile once, then use the home screen to start quizzes fast."
    )


def build_returning_welcome_message(
    first_name: str | None,
    bot_theme: BotThemeConfig | None = None,
) -> str:
    learner_name = first_name or "there"
    if bot_theme and bot_theme.returning_message_template:
        return bot_theme.returning_message_template.format(
            brand_name=bot_theme.brand_name,
            learner_name=learner_name,
        )
    prefix = bot_theme.brand_name if bot_theme else "Study Bot"
    return f"👋 Welcome back, {learner_name}! Tap below to get started.\n— {prefix}"


def build_home_message(
    profile: Mapping[str, str | None],
    bot_theme: BotThemeConfig | None = None,
) -> str:
    faculty = profile.get("faculty_name") or "Not set"
    program = profile.get("program_name") or "Not set"
    level = profile.get("level_name") or "Not set"
    semester = profile.get("semester_name") or "Not set"
    heading = "Study Home"
    if bot_theme is not None:
        heading = f"{bot_theme.brand_name} Study Home"

    return (
        f"{heading}\n\n"
        f"Faculty: {faculty}\n"
        f"Program: {program}\n"
        f"Level: {level}\n"
        f"Semester: {semester}"
    )


def build_help_message(bot_theme: BotThemeConfig | None = None) -> str:
    if bot_theme is None:
        return (
            "Use Start Quiz to begin studying, Change Course to update your course, "
            "and Performance to review your progress when it is connected."
        )

    start_label = _button_label("start_quiz", "Start Quiz", bot_theme)
    settings_label = _button_label("study_settings", "Study Settings", bot_theme)
    performance_label = _button_label("performance", "Performance", bot_theme)
    return (
        f"Use {start_label} to begin studying, {settings_label} to update your course, "
        f"and {performance_label} to review your progress when it is connected."
    )


def build_performance_placeholder() -> str:
    return "Performance summaries will show here once the home flow is fully wired."


def build_question_action_prompt() -> str:
    return "Need to flag this question?"


def build_answer_action_prompt() -> str:
    return "Not correct? Report this answer if the key or explanation is off."


def build_report_reason_prompt(scope: str) -> str:
    if scope == "question":
        return "What is wrong with this question?"
    return "What is wrong with this answer or explanation?"


def build_report_note_prompt(scope: str) -> str:
    if scope == "question":
        return "Send any extra detail as your next message, or tap Skip note."
    return "Send any extra detail about the answer issue as your next message, or tap Skip note."


def build_report_confirmation_message() -> str:
    return "Thanks. Your report has been submitted."


def build_report_cancelled_message() -> str:
    return "Report cancelled."


def _build_accuracy_coaching(summary: dict) -> str:
    accuracy = summary["accuracy_percent"]
    if accuracy >= 85:
        return "Excellent work. You are handling this topic well."
    if accuracy >= 65:
        return "Solid work. A quick review should sharpen the weaker spots."
    return "Keep going, this topic needs another pass."


def _build_pace_text(summary: dict) -> str:
    return f"About {summary['average_time_seconds']}s per question"


def _build_timing_line(summary: dict, *, key: str, emoji: str, label: str) -> str | None:
    question = summary.get(key)
    if not question:
        return None
    return f"{emoji} {label}: Question {question['question_number']} - {question['time_seconds']}s"


def build_quiz_completion_message(summary: dict) -> str:
    weakest_topic = summary.get("weakest_topic") or "No weak topic detected"
    strongest_topic = summary.get("strongest_topic") or "No standout topic yet"
    lines = [
        f"📘 {summary['course_name']} Quiz Complete",
        "",
        f"📝 Score: {summary['score']}/{summary['total_questions']} correct",
        f"🎯 Accuracy: {summary['accuracy_percent']}% - {_build_accuracy_coaching(summary)}",
        f"⏱ Pace: {_build_pace_text(summary)}",
        "",
        f"💪 Strongest area: {strongest_topic}",
        f"📌 Focus next: {weakest_topic}",
    ]

    longest_line = _build_timing_line(
        summary,
        key="longest_question",
        emoji="🐢",
        label="Longest",
    )
    fastest_line = _build_timing_line(
        summary,
        key="fastest_question",
        emoji="⚡",
        label="Fastest",
    )
    if longest_line or fastest_line:
        lines.append("")
        if longest_line:
            lines.append(longest_line)
        if fastest_line:
            lines.append(fastest_line)

    lines.extend(
        [
            "",
            f"Next step: {summary['recommendation']}",
        ]
    )
    return "\n".join(lines)


def build_performance_message(summary: dict | None) -> str:
    if not summary or summary.get("attempt_count", 0) == 0:
        return (
            "📊 Your Performance\n\n"
            "No quiz history yet.\n"
            "Finish a quiz and your progress summary will appear here."
        )

    strongest_course = summary.get("strongest_course") or "Not enough data"
    weakest_course = summary.get("weakest_course") or "Not enough data"
    accuracy = summary["accuracy_percent"]
    if accuracy >= 85:
        coaching = "Excellent consistency. Keep stretching with tougher quizzes."
    elif accuracy >= 65:
        coaching = "Solid progress. A few more quizzes should lift your weak areas."
    else:
        coaching = "Keep going. A few short quizzes in your weak course should raise your overall accuracy."
    return (
        "📊 Your Performance\n\n"
        f"📝 Quizzes completed: {summary['quiz_count']}\n"
        f"❓ Questions answered: {summary['attempt_count']}\n"
        f"🎯 Overall accuracy: {summary['accuracy_percent']}%\n"
        f"⏱ Average pace: {summary['average_time_seconds']}s per question\n\n"
        f"💪 Strongest course: {strongest_course}\n"
        f"📌 Focus next: {weakest_course}\n\n"
        f"{coaching}\n"
        f"Next step: {summary['recommendation']}"
    )


def build_quiz_ready_message(course_name: str | None, question_count: int) -> str:
    if course_name:
        return (
            f"Your {question_count}-question quiz for {course_name} will start here "
            "once the quiz session wiring is connected."
        )
    return (
        f"Your {question_count}-question quiz will start here once your course is set "
        "and the quiz session wiring is connected."
    )


def build_missing_course_message() -> str:
    return "Choose your course first so the bot knows where to start."


def build_quiz_course_prompt(program_name: str | None, level_name: str | None) -> str:
    details = ", ".join(part for part in (program_name, level_name) if part)
    if details:
        return f"Choose a course for your quiz.\n\n{details}"
    return "Choose a course for your quiz."


def build_no_questions_available_message(course_name: str) -> str:
    return f"No questions are available for {course_name} yet."


def build_incomplete_study_profile_message() -> str:
    return "Complete your study profile first so I can show the right courses for your programme."
