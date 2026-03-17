from collections.abc import Mapping


def build_welcome_message(first_name: str | None) -> str:
    learner_name = first_name or "student"
    return (
        f"Welcome, {learner_name}.\n\n"
        "Set up your study profile once, then use the home screen to start quizzes fast."
    )


def build_home_message(profile: Mapping[str, str | None]) -> str:
    semester = profile.get("semester_name") or "Not set"
    course = profile.get("course_name") or "No course selected"
    faculty = profile.get("faculty_name") or "Not set"
    program = profile.get("program_name") or "Not set"
    level = profile.get("level_name") or "Not set"

    return (
        "Study Home\n\n"
        f"Faculty: {faculty}\n"
        f"Program: {program}\n"
        f"Level: {level}\n"
        f"Semester: {semester}\n"
        f"Course: {course}"
    )


def build_help_message() -> str:
    return (
        "Use Start Quiz to begin studying, Change Course to update your course, "
        "and Performance to review your progress when it is connected."
    )


def build_performance_placeholder() -> str:
    return "Performance summaries will show here once the home flow is fully wired."


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
