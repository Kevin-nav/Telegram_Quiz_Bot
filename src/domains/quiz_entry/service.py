class QuizEntryService:
    QUESTION_COUNTS = (10, 20, 30)

    def build_length_prompt(self, course_name: str | None) -> str:
        if course_name:
            return f"How many questions would you like for {course_name}?"
        return "Choose your course first, then pick a quiz length."

    def build_quiz_ready_message(self, course_name: str | None, question_count: int) -> str:
        if course_name:
            return (
                f"Your {question_count}-question quiz for {course_name} will start here "
                "once the quiz session wiring is connected."
            )
        return (
            f"Your {question_count}-question quiz will start here once your course is set "
            "and the quiz session wiring is connected."
        )

    def build_continue_placeholder(self) -> str:
        return "Continue Quiz is reserved for active sessions and will be connected next."

    def build_performance_placeholder(self) -> str:
        return "Performance summaries will appear here once the home flow is fully wired."

    def build_help_message(self) -> str:
        return (
            "Use Start Quiz to begin studying, Change Course to update your academic "
            "context, and Performance to review your progress once it is connected."
        )
