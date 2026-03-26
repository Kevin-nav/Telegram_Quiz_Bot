from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import random
from typing import Any, Sequence

from src.domains.adaptive.models import AdaptiveQuestionProfile, AdaptiveStudentState
from src.domains.adaptive.selection import select_questions as select_adaptive_questions
from src.domains.adaptive.updater import (
    AdaptiveUpdateResult,
    apply_attempt_update as apply_adaptive_attempt_update,
)
from src.infra.db.repositories.question_attempt_repository import QuestionAttemptRepository
from src.infra.db.repositories.question_bank_repository import QuestionBankRepository
from src.infra.db.repositories.student_course_state_repository import (
    StudentCourseStateRepository,
)
from src.infra.db.repositories.student_question_srs_repository import (
    StudentQuestionSrsRepository,
)
from src.infra.redis.state_store import InteractiveStateStore


@dataclass(slots=True)
class AdaptiveSelectionOutput:
    student_state: AdaptiveStudentState
    selected_questions: list[AdaptiveQuestionProfile]
    question_rows: list[Any]


class AdaptiveLearningService:
    def __init__(
        self,
        *,
        question_bank_repository: QuestionBankRepository | None = None,
        question_attempt_repository: QuestionAttemptRepository | None = None,
        student_course_state_repository: StudentCourseStateRepository | None = None,
        student_question_srs_repository: StudentQuestionSrsRepository | None = None,
        state_store: InteractiveStateStore | None = None,
    ):
        self.question_bank_repository = question_bank_repository or QuestionBankRepository()
        self.question_attempt_repository = (
            question_attempt_repository or QuestionAttemptRepository()
        )
        self.student_course_state_repository = (
            student_course_state_repository or StudentCourseStateRepository()
        )
        self.student_question_srs_repository = (
            student_question_srs_repository or StudentQuestionSrsRepository()
        )
        self.state_store = state_store

    async def select_questions(
        self,
        *,
        user_id: int,
        course_id: str,
        quiz_length: int,
        current_session_question_ids: set[str] | None = None,
        recently_correct_at_by_question: dict[str, datetime] | None = None,
        attempts_by_question: dict[str, Sequence[Any]] | None = None,
        attempted_question_ids: set[str] | None = None,
        srs_by_question: dict[str, Any] | None = None,
        now: datetime | None = None,
        rng: random.Random | None = None,
    ) -> AdaptiveSelectionOutput:
        student_state = await self._load_student_state(user_id, course_id)
        question_rows = await self.question_bank_repository.list_ready_questions(course_id)
        question_profiles = [self._question_row_to_profile(row) for row in question_rows]
        attempts_by_question, recently_correct_at_by_question, attempted_question_ids = (
            await self._load_attempt_inputs(
                user_id,
                question_rows,
                attempts_by_question=attempts_by_question,
                recently_correct_at_by_question=recently_correct_at_by_question,
                attempted_question_ids=attempted_question_ids,
            )
        )
        srs_by_question = await self._load_srs_by_question(
            user_id,
            question_rows,
            provided=srs_by_question,
        )

        selected_questions = select_adaptive_questions(
            question_profiles,
            student_state,
            quiz_length,
            current_session_question_ids=current_session_question_ids,
            recently_correct_at_by_question=recently_correct_at_by_question,
            attempts_by_question=attempts_by_question,
            attempted_question_ids=attempted_question_ids,
            srs_by_question=srs_by_question,
            now=now,
            rng=rng,
        )
        return AdaptiveSelectionOutput(
            student_state=student_state,
            selected_questions=selected_questions,
            question_rows=question_rows,
        )

    async def apply_attempt_update(
        self,
        *,
        user_id: int,
        course_id: str,
        question: AdaptiveQuestionProfile,
        is_correct: bool,
        time_taken_seconds: float | None = None,
        time_allocated_seconds: int | None = None,
        selected_distractor: str | None = None,
        attempts_for_question: Sequence[Any] | None = None,
        processing_target: str | None = None,
        now: datetime | None = None,
    ) -> AdaptiveUpdateResult:
        student_state = await self._load_student_state(user_id, course_id)
        result = apply_adaptive_attempt_update(
            student_state,
            question,
            is_correct=is_correct,
            time_taken_seconds=time_taken_seconds,
            time_allocated_seconds=time_allocated_seconds,
            selected_distractor=selected_distractor,
            attempts_for_question=attempts_for_question,
            processing_target=processing_target,
            now=now,
        )
        await self.student_course_state_repository.update_fields(
            user_id,
            course_id,
            overall_skill=result.student_state.overall_skill,
            topic_skills=result.student_state.topic_skills,
            cognitive_profile=result.student_state.cognitive_profile,
            processing_profile=result.student_state.processing_profile,
            misconception_flags=result.student_state.misconception_flags,
            phase=result.student_state.phase,
            total_quizzes_completed=result.student_state.total_quizzes_completed,
            total_attempts=result.student_state.total_attempts,
        )
        if self.state_store is not None:
            await self.state_store.invalidate_adaptive_snapshot(user_id, course_id)
        return result

    async def increment_completed_quizzes(self, *, user_id: int, course_id: str) -> None:
        await self.student_course_state_repository.increment_counters(
            user_id,
            course_id,
            quizzes=1,
        )
        if self.state_store is not None:
            await self.state_store.invalidate_adaptive_snapshot(user_id, course_id)

    async def _load_student_state(
        self, user_id: int, course_id: str
    ) -> AdaptiveStudentState:
        if self.state_store is not None:
            cached_snapshot = await self.state_store.get_adaptive_snapshot(user_id, course_id)
            if cached_snapshot is not None:
                exam_date = cached_snapshot.get("exam_date")
                return AdaptiveStudentState(
                    **{
                        **cached_snapshot,
                        "exam_date": datetime.fromisoformat(exam_date) if exam_date else None,
                    }
                )

        state = await self.student_course_state_repository.get_or_create(user_id, course_id)
        snapshot = AdaptiveStudentState(
            overall_skill=state.overall_skill,
            topic_skills=dict(state.topic_skills or {}),
            cognitive_profile=dict(state.cognitive_profile or {}),
            processing_profile=dict(state.processing_profile or {}),
            misconception_flags=list(state.misconception_flags or []),
            phase=state.phase,
            total_quizzes_completed=state.total_quizzes_completed,
            total_attempts=state.total_attempts,
            exam_date=state.exam_date,
        )
        if self.state_store is not None:
            await self.state_store.set_adaptive_snapshot(
                user_id,
                course_id,
                {
                    "overall_skill": snapshot.overall_skill,
                    "topic_skills": snapshot.topic_skills,
                    "cognitive_profile": snapshot.cognitive_profile,
                    "processing_profile": snapshot.processing_profile,
                    "misconception_flags": snapshot.misconception_flags,
                    "phase": snapshot.phase,
                    "total_quizzes_completed": snapshot.total_quizzes_completed,
                    "total_attempts": snapshot.total_attempts,
                    "exam_date": snapshot.exam_date.isoformat() if snapshot.exam_date else None,
                },
            )
        return snapshot

    async def _load_srs_by_question(
        self,
        user_id: int,
        question_rows: Sequence[Any],
        *,
        provided: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if provided is not None:
            return provided

        question_ids_by_key: dict[str, int] = {
            row.question_key: row.id
            for row in question_rows
            if getattr(row, "id", None) is not None
        }
        if not question_ids_by_key:
            return {}

        records = await self.student_question_srs_repository.get_many(
            user_id,
            question_ids_by_key.values(),
        )
        return {
            question_key: records[question_id]
            for question_key, question_id in question_ids_by_key.items()
            if question_id in records
        }

    async def _load_attempt_inputs(
        self,
        user_id: int,
        question_rows: Sequence[Any],
        *,
        attempts_by_question: dict[str, Sequence[Any]] | None = None,
        recently_correct_at_by_question: dict[str, datetime] | None = None,
        attempted_question_ids: set[str] | None = None,
    ) -> tuple[dict[str, Sequence[Any]], dict[str, datetime], set[str]]:
        if (
            attempts_by_question is not None
            and recently_correct_at_by_question is not None
            and attempted_question_ids is not None
        ):
            return (
                attempts_by_question,
                recently_correct_at_by_question,
                attempted_question_ids,
            )

        question_keys_by_id = {
            row.id: row.question_key
            for row in question_rows
            if getattr(row, "id", None) is not None
        }
        if not question_keys_by_id:
            return (
                attempts_by_question or {},
                recently_correct_at_by_question or {},
                set(attempted_question_ids or ()),
            )

        attempts_by_row_id = await self.question_attempt_repository.list_attempts_for_questions(
            user_id=user_id,
            question_ids=question_keys_by_id.keys(),
        )
        loaded_attempts_by_question: dict[str, Sequence[Any]] = {}
        loaded_recently_correct_at_by_question: dict[str, datetime] = {}
        loaded_attempted_question_ids: set[str] = set()

        for question_id, attempts in attempts_by_row_id.items():
            question_key = question_keys_by_id.get(question_id)
            if question_key is None:
                continue

            loaded_attempts_by_question[question_key] = attempts
            if attempts:
                loaded_attempted_question_ids.add(question_key)

            correct_timestamps = [
                getattr(attempt, "created_at", None)
                for attempt in attempts
                if getattr(attempt, "is_correct", False)
                and getattr(attempt, "created_at", None) is not None
            ]
            if correct_timestamps:
                loaded_recently_correct_at_by_question[question_key] = max(correct_timestamps)

        return (
            attempts_by_question or loaded_attempts_by_question,
            recently_correct_at_by_question or loaded_recently_correct_at_by_question,
            set(attempted_question_ids or loaded_attempted_question_ids),
        )

    def _question_row_to_profile(self, row: Any) -> AdaptiveQuestionProfile:
        return AdaptiveQuestionProfile(
            question_id=row.question_key,
            topic_id=row.topic_id,
            scaled_score=row.scaled_score,
            band=row.band,
            cognitive_level=row.cognitive_level,
            processing_complexity=row.processing_complexity,
            distractor_complexity=row.distractor_complexity,
            note_reference=row.note_reference,
            question_type=row.question_type,
            option_count=row.option_count,
            has_latex=bool(row.has_latex),
            arrangement_hash=None,
            config_index=None,
        )
