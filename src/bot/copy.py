from collections.abc import Mapping


def build_welcome_message(first_name: str | None) -> str:
    learner_name = first_name or "student"
    return (
        f"Welcome, {learner_name}.\n\n"
        "Set up your study profile once, then use the home screen to start quizzes fast."
    )


def build_home_message(profile: Mapping[str, str | None]) -> str:
    faculty = profile.get("faculty_name") or "Not set"
    program = profile.get("program_name") or "Not set"
    level = profile.get("level_name") or "Not set"
    semester = profile.get("semester_name") or "Not set"

    return (
        "Study Home\n\n"
        f"Faculty: {faculty}\n"
        f"Program: {program}\n"
        f"Level: {level}\n"
        f"Semester: {semester}"
    )


def build_help_message() -> str:
    return (
        "Use Start Quiz to begin studying, Change Course to update your course, "
        "and Performance to review your progress when it is connected."
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


def build_quiz_completion_message(summary: dict) -> str:
    weakest_topic = summary.get("weakest_topic") or "No weak topic detected"
    strongest_topic = summary.get("strongest_topic") or "No standout topic yet"
    return (
        f"Quiz complete for {summary['course_name']}.\n\n"
        f"Score: {summary['score']}/{summary['total_questions']}\n"
        f"Accuracy: {summary['accuracy_percent']}%\n"
        f"Result: {summary['tier']}\n"
        f"Average pace: {summary['average_time_seconds']}s per question\n"
        f"Strongest topic: {strongest_topic}\n"
        f"Weakest topic: {weakest_topic}\n"
        f"Next step: {summary['recommendation']}"
    )


def build_performance_message(summary: dict | None) -> str:
    if not summary or summary.get("attempt_count", 0) == 0:
        return "No quiz history yet. Finish a quiz and your performance summary will appear here."

    strongest_course = summary.get("strongest_course") or "Not enough data"
    weakest_course = summary.get("weakest_course") or "Not enough data"
    return (
        "Performance\n\n"
        f"Quizzes completed: {summary['quiz_count']}\n"
        f"Questions answered: {summary['attempt_count']}\n"
        f"Overall accuracy: {summary['accuracy_percent']}%\n"
        f"Average response time: {summary['average_time_seconds']}s\n"
        f"Strongest course: {strongest_course}\n"
        f"Weakest course: {weakest_course}\n"
        f"Focus next: {summary['recommendation']}"
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
