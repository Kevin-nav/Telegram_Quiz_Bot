from __future__ import annotations

from src.domains.quiz.models import QuizQuestion, QuizSessionState


QUESTION_REPORT_REASONS = {
    "not_related_to_course",
    "question_unclear",
    "image_or_latex_issue",
    "duplicate_question",
    "other",
}

ANSWER_REPORT_REASONS = {
    "marked_wrong_but_my_answer_is_right",
    "correct_answer_shown_is_wrong",
    "explanation_is_wrong",
    "other",
}


class QuizReportingService:
    def validate_reason(self, report_scope: str, report_reason: str) -> None:
        allowed = self._allowed_reasons(report_scope)
        if report_reason not in allowed:
            raise ValueError(
                f"Invalid report reason {report_reason!r} for scope {report_scope!r}."
            )

    def build_report_payload(
        self,
        *,
        session: QuizSessionState,
        report_scope: str,
        report_reason: str,
        report_note: str | None,
    ) -> dict:
        self.validate_reason(report_scope, report_reason)
        question, question_index = self._question_context(session, report_scope)

        return {
            "user_id": session.user_id,
            "session_id": session.session_id,
            "course_id": session.course_id,
            "question_id": question.source_question_id,
            "question_key": question.question_id,
            "question_index": question_index,
            "report_scope": report_scope,
            "report_reason": report_reason,
            "report_note": report_note,
            "report_metadata": {
                "correct_option_id": question.correct_option_id,
                "correct_option_text": question.options[question.correct_option_id],
                "has_explanation": bool(question.explanation),
                "has_latex": question.has_latex,
                "arrangement_hash": question.arrangement_hash,
                "config_index": question.config_index,
                "question_asset_url": question.question_asset_url,
                "explanation_asset_url": question.explanation_asset_url,
            },
        }

    def _allowed_reasons(self, report_scope: str) -> set[str]:
        if report_scope == "question":
            return QUESTION_REPORT_REASONS
        if report_scope == "answer":
            return ANSWER_REPORT_REASONS
        raise ValueError(f"Unsupported report scope {report_scope!r}.")

    def _question_context(
        self, session: QuizSessionState, report_scope: str
    ) -> tuple[QuizQuestion, int]:
        if report_scope == "question":
            question = session.current_question()
            if question is None:
                raise ValueError("No active question available for question report.")
            return question, session.current_index

        if report_scope == "answer":
            question_index = session.last_answered_question_index
            if question_index is None or not (0 <= question_index < len(session.questions)):
                raise ValueError("No answered question available for answer report.")
            return session.questions[question_index], question_index

        raise ValueError(f"Unsupported report scope {report_scope!r}.")
