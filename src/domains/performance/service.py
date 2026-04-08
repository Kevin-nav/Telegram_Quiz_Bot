from __future__ import annotations

from collections import defaultdict

from src.bot.runtime_config import TANJAH_BOT_ID
from src.infra.db.repositories.question_attempt_repository import QuestionAttemptRepository
from src.infra.db.repositories.student_course_state_repository import (
    StudentCourseStateRepository,
)


class PerformanceService:
    def __init__(
        self,
        question_attempt_repository: QuestionAttemptRepository | None = None,
        student_course_state_repository: StudentCourseStateRepository | None = None,
        bot_id: str = TANJAH_BOT_ID,
    ):
        self.question_attempt_repository = (
            question_attempt_repository or QuestionAttemptRepository()
        )
        self.student_course_state_repository = (
            student_course_state_repository or StudentCourseStateRepository()
        )
        self.bot_id = bot_id

    async def get_summary(self, user_id: int) -> dict:
        course_states = await self.student_course_state_repository.list_for_user(
            user_id,
            bot_id=self.bot_id,
        )
        denormalized_summary = self.build_summary_from_course_states(course_states)
        if denormalized_summary is not None:
            return denormalized_summary

        attempts = await self.question_attempt_repository.list_attempts_for_user(
            user_id=user_id,
            bot_id=self.bot_id,
        )
        return self.build_summary_from_attempts(attempts)

    def build_summary_from_course_states(self, course_states: list) -> dict | None:
        active_states = [
            state
            for state in course_states
            if int(getattr(state, "total_attempts", 0) or 0) > 0
        ]
        if not active_states:
            return None

        quiz_count = sum(int(getattr(state, "total_quizzes_completed", 0) or 0) for state in active_states)
        attempt_count = sum(int(getattr(state, "total_attempts", 0) or 0) for state in active_states)
        correct_count = sum(int(getattr(state, "total_correct", 0) or 0) for state in active_states)
        accuracy_percent = round((correct_count / attempt_count) * 100) if attempt_count else 0
        weighted_time = sum(
            float(getattr(state, "avg_time_per_question", 0) or 0)
            * int(getattr(state, "total_attempts", 0) or 0)
            for state in active_states
            if getattr(state, "avg_time_per_question", None) is not None
        )
        average_time_seconds = round(weighted_time / attempt_count, 1) if attempt_count else 0.0

        ranked_courses = sorted(
            (
                (
                    (
                        int(getattr(state, "total_correct", 0) or 0)
                        / max(1, int(getattr(state, "total_attempts", 0) or 0))
                    ),
                    state.course_id,
                )
                for state in active_states
            ),
            key=lambda item: (item[0], item[1]),
        )
        strongest_course = ranked_courses[-1][1].replace("-", " ").title()
        weakest_course = ranked_courses[0][1].replace("-", " ").title()
        recommendation = (
            f"Review {weakest_course} next."
            if weakest_course != strongest_course
            else f"Keep reinforcing {strongest_course} with another round."
        )
        return {
            "quiz_count": quiz_count,
            "attempt_count": attempt_count,
            "accuracy_percent": accuracy_percent,
            "average_time_seconds": average_time_seconds,
            "strongest_course": strongest_course,
            "weakest_course": weakest_course,
            "recommendation": recommendation,
        }

    def build_summary_from_attempts(self, attempts: list) -> dict:
        if not attempts:
            return {
                "quiz_count": 0,
                "attempt_count": 0,
                "accuracy_percent": 0,
                "average_time_seconds": 0.0,
                "strongest_course": None,
                "weakest_course": None,
                "recommendation": "Finish a quiz to unlock your study insights.",
            }

        quiz_count = len({attempt.session_id for attempt in attempts})
        attempt_count = len(attempts)
        correct_count = sum(1 for attempt in attempts if attempt.is_correct)
        accuracy_percent = round((correct_count / attempt_count) * 100)
        timed_attempts = [
            float(attempt.time_taken_seconds)
            for attempt in attempts
            if attempt.time_taken_seconds is not None
        ]
        average_time_seconds = round(
            sum(timed_attempts) / len(timed_attempts), 1
        ) if timed_attempts else 0.0

        course_buckets: dict[str, list[bool]] = defaultdict(list)
        for attempt in attempts:
            course_buckets[attempt.course_id].append(bool(attempt.is_correct))

        ranked_courses = sorted(
            (
                (
                    round(sum(1 for result in results if result) / len(results), 4),
                    course_id,
                )
                for course_id, results in course_buckets.items()
            ),
            key=lambda item: (item[0], item[1]),
        )
        strongest_course = ranked_courses[-1][1].replace("-", " ").title()
        weakest_course = ranked_courses[0][1].replace("-", " ").title()

        recommendation = (
            f"Review {weakest_course} next."
            if weakest_course != strongest_course
            else f"Keep reinforcing {strongest_course} with another round."
        )

        return {
            "quiz_count": quiz_count,
            "attempt_count": attempt_count,
            "accuracy_percent": accuracy_percent,
            "average_time_seconds": average_time_seconds,
            "strongest_course": strongest_course,
            "weakest_course": weakest_course,
            "recommendation": recommendation,
        }
