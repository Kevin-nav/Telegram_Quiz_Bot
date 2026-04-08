from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import random
from typing import Any, Sequence

from src.domains.adaptive.models import (
    AdaptiveQuestionProfile,
    AdaptiveStudentState,
    AttemptHistorySummary,
    SrsState,
)
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


@dataclass(slots=True)
class AdaptiveQuestionManifestEntry:
    source_question_id: int
    profile: AdaptiveQuestionProfile


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
        bot_id: str | None = None,
        course_id: str,
        quiz_length: int,
        current_session_question_ids: set[str] | None = None,
        recently_correct_at_by_question: dict[str, datetime] | None = None,
        attempts_by_question: dict[str, Any] | None = None,
        attempted_question_ids: set[str] | None = None,
        srs_by_question: dict[str, Any] | None = None,
        now: datetime | None = None,
        rng: random.Random | None = None,
    ) -> AdaptiveSelectionOutput:
        student_state = await self._load_student_state(user_id, course_id, bot_id=bot_id)
        manifest_entries = await self._load_question_manifest(course_id)
        question_profiles = [entry.profile for entry in manifest_entries]
        question_ids_by_key = {
            entry.profile.question_id: entry.source_question_id for entry in manifest_entries
        }
        (
            attempts_by_question,
            recently_correct_at_by_question,
            attempted_question_ids,
            srs_by_question,
        ) = await self._load_selector_inputs(
            user_id,
            course_id,
            question_ids_by_key,
            attempts_by_question=attempts_by_question,
            recently_correct_at_by_question=recently_correct_at_by_question,
            attempted_question_ids=attempted_question_ids,
            srs_by_question=srs_by_question,
            bot_id=bot_id,
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
        question_rows = await self._load_selected_question_rows(selected_questions)
        return AdaptiveSelectionOutput(
            student_state=student_state,
            selected_questions=selected_questions,
            question_rows=question_rows,
        )

    async def apply_attempt_update(
        self,
        *,
        user_id: int,
        bot_id: str | None = None,
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
        student_state = await self._load_student_state(user_id, course_id, bot_id=bot_id)
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
            bot_id=bot_id,
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

    async def increment_completed_quizzes(
        self,
        *,
        user_id: int,
        course_id: str,
        bot_id: str | None = None,
    ) -> None:
        await self.student_course_state_repository.increment_counters(
            user_id,
            course_id,
            bot_id=bot_id,
            quizzes=1,
        )
        if self.state_store is not None:
            await self.state_store.invalidate_adaptive_snapshot(user_id, course_id)

    async def _load_student_state(
        self, user_id: int, course_id: str, *, bot_id: str | None = None
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

        state = await self.student_course_state_repository.get_or_create(
            user_id,
            course_id,
            bot_id=bot_id,
        )
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

    async def _load_question_manifest(self, course_id: str) -> list[AdaptiveQuestionManifestEntry]:
        if self.state_store is not None:
            cached_manifest = await self.state_store.get_course_question_manifest(course_id)
            if cached_manifest is not None:
                return [self._manifest_payload_to_entry(item) for item in cached_manifest]

        manifest_rows = await self.question_bank_repository.list_ready_question_manifest(course_id)
        manifest_entries = [self._manifest_payload_to_entry(item) for item in manifest_rows]
        if self.state_store is not None:
            await self.state_store.set_course_question_manifest(course_id, manifest_rows)
        return manifest_entries

    async def _load_selector_inputs(
        self,
        user_id: int,
        course_id: str,
        question_ids_by_key: dict[str, int],
        *,
        attempts_by_question: dict[str, Any] | None = None,
        recently_correct_at_by_question: dict[str, datetime] | None = None,
        attempted_question_ids: set[str] | None = None,
        srs_by_question: dict[str, Any] | None = None,
        bot_id: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, datetime], set[str], dict[str, Any]]:
        if (
            attempts_by_question is not None
            and recently_correct_at_by_question is not None
            and attempted_question_ids is not None
            and srs_by_question is not None
        ):
            return (
                attempts_by_question,
                recently_correct_at_by_question,
                attempted_question_ids,
                srs_by_question,
            )

        cached_snapshot = None
        if self.state_store is not None:
            cached_snapshot = await self.state_store.get_selector_snapshot(user_id, course_id)

        loaded_attempts_by_question = attempts_by_question
        if loaded_attempts_by_question is None and cached_snapshot is not None:
            loaded_attempts_by_question = self._deserialize_cached_attempts(cached_snapshot)

        loaded_recently_correct = recently_correct_at_by_question
        if loaded_recently_correct is None and cached_snapshot is not None:
            loaded_recently_correct = self._deserialize_cached_recently_correct(cached_snapshot)

        loaded_attempted_question_ids = (
            set(attempted_question_ids) if attempted_question_ids is not None else None
        )
        if loaded_attempted_question_ids is None and cached_snapshot is not None:
            loaded_attempted_question_ids = self._deserialize_cached_attempted_question_ids(
                cached_snapshot
            )

        loaded_srs_by_question = srs_by_question
        if loaded_srs_by_question is None and cached_snapshot is not None:
            loaded_srs_by_question = self._deserialize_cached_srs(cached_snapshot)

        if (
            loaded_attempts_by_question is None
            or loaded_recently_correct is None
            or loaded_attempted_question_ids is None
            or loaded_srs_by_question is None
        ):
            question_ids = tuple(question_ids_by_key.values())
            if not question_ids:
                return (
                    loaded_attempts_by_question or {},
                    loaded_recently_correct or {},
                    loaded_attempted_question_ids or set(),
                    loaded_srs_by_question or {},
                )

            if loaded_attempts_by_question is None or loaded_attempted_question_ids is None:
                attempt_summaries_by_row_id = (
                    await self.question_attempt_repository.summarize_attempts_for_questions(
                        user_id=user_id,
                        question_ids=question_ids,
                        bot_id=bot_id,
                    )
                )
                loaded_attempts_by_question = dict(loaded_attempts_by_question or {})
                for question_key, question_id in question_ids_by_key.items():
                    if question_key in loaded_attempts_by_question:
                        continue
                    summary = attempt_summaries_by_row_id.get(question_id)
                    if summary is not None and summary.total_attempts > 0:
                        loaded_attempts_by_question[question_key] = summary

            if loaded_recently_correct is None or loaded_srs_by_question is None:
                srs_records = await self.student_question_srs_repository.get_many(
                    user_id,
                    question_ids,
                    bot_id=bot_id,
                )
                if loaded_recently_correct is None:
                    loaded_recently_correct = {
                        question_key: record.last_correct_at
                        for question_key, question_id in question_ids_by_key.items()
                        if (record := srs_records.get(question_id)) is not None
                        and record.last_correct_at is not None
                    }
                if loaded_srs_by_question is None:
                    loaded_srs_by_question = {
                        question_key: SrsState(
                            box=record.box,
                            last_presented_at=record.last_presented_at,
                            last_correct_at=record.last_correct_at,
                            last_transition_at=record.last_transition_at,
                        )
                        for question_key, question_id in question_ids_by_key.items()
                        if (record := srs_records.get(question_id)) is not None
                    }

            if loaded_attempted_question_ids is None:
                loaded_attempted_question_ids = {
                    question_key
                    for question_key, summary in (loaded_attempts_by_question or {}).items()
                    if self._has_attempt_history(summary)
                }

            if self.state_store is not None:
                await self.state_store.set_selector_snapshot(
                    user_id,
                    course_id,
                    self._serialize_selector_snapshot(
                        attempts_by_question=loaded_attempts_by_question or {},
                        recently_correct_at_by_question=loaded_recently_correct or {},
                        attempted_question_ids=loaded_attempted_question_ids or set(),
                        srs_by_question=loaded_srs_by_question or {},
                    ),
                )

        return (
            loaded_attempts_by_question or {},
            loaded_recently_correct or {},
            loaded_attempted_question_ids or set(),
            loaded_srs_by_question or {},
        )

    async def _load_selected_question_rows(
        self,
        selected_questions: Sequence[AdaptiveQuestionProfile],
    ) -> list[Any]:
        selected_question_keys = [question.question_id for question in selected_questions]
        if not selected_question_keys:
            return []

        question_rows = await self.question_bank_repository.list_questions_by_keys(
            selected_question_keys
        )
        question_rows_by_key = {
            row.question_key: row for row in question_rows if hasattr(row, "question_key")
        }
        return [
            question_rows_by_key[question_key]
            for question_key in selected_question_keys
            if question_key in question_rows_by_key
        ]

    def _manifest_payload_to_entry(self, payload: dict) -> AdaptiveQuestionManifestEntry:
        return AdaptiveQuestionManifestEntry(
            source_question_id=int(payload["source_question_id"]),
            profile=AdaptiveQuestionProfile(
                question_id=payload["question_key"],
                topic_id=payload["topic_id"],
                scaled_score=float(payload["scaled_score"]),
                band=int(payload.get("band", 3) or 3),
                cognitive_level=payload.get("cognitive_level"),
                processing_complexity=payload.get("processing_complexity"),
                distractor_complexity=payload.get("distractor_complexity"),
                note_reference=payload.get("note_reference"),
                question_type=payload.get("question_type", "MCQ"),
                option_count=int(payload.get("option_count", 4) or 4),
                has_latex=bool(payload.get("has_latex", False)),
                arrangement_hash=None,
                config_index=None,
            ),
        )

    def _serialize_selector_snapshot(
        self,
        *,
        attempts_by_question: dict[str, Any],
        recently_correct_at_by_question: dict[str, datetime],
        attempted_question_ids: set[str],
        srs_by_question: dict[str, Any],
    ) -> dict:
        return {
            "attempts_by_question": {
                question_key: {
                    "total_attempts": self._attempt_summary(summary).total_attempts,
                    "wrong_attempts": self._attempt_summary(summary).wrong_attempts,
                    "last_wrong_at": (
                        self._attempt_summary(summary).last_wrong_at.isoformat()
                        if self._attempt_summary(summary).last_wrong_at is not None
                        else None
                    ),
                }
                for question_key, summary in attempts_by_question.items()
            },
            "recently_correct_at_by_question": {
                question_key: timestamp.isoformat()
                for question_key, timestamp in recently_correct_at_by_question.items()
                if timestamp is not None
            },
            "attempted_question_ids": sorted(attempted_question_ids),
            "srs_by_question": {
                question_key: {
                    "box": int(getattr(srs_state, "box", 0) or 0),
                    "last_presented_at": (
                        getattr(srs_state, "last_presented_at", None).isoformat()
                        if getattr(srs_state, "last_presented_at", None) is not None
                        else None
                    ),
                    "last_correct_at": (
                        getattr(srs_state, "last_correct_at", None).isoformat()
                        if getattr(srs_state, "last_correct_at", None) is not None
                        else None
                    ),
                    "last_transition_at": (
                        getattr(srs_state, "last_transition_at", None).isoformat()
                        if getattr(srs_state, "last_transition_at", None) is not None
                        else None
                    ),
                }
                for question_key, srs_state in srs_by_question.items()
            },
        }

    def _deserialize_cached_attempts(self, snapshot: dict | None) -> dict[str, AttemptHistorySummary]:
        if snapshot is None:
            return {}
        attempts_payload = snapshot.get("attempts_by_question") or {}
        return {
            question_key: AttemptHistorySummary(
                total_attempts=int(payload.get("total_attempts", 0) or 0),
                wrong_attempts=int(payload.get("wrong_attempts", 0) or 0),
                last_wrong_at=(
                    datetime.fromisoformat(payload["last_wrong_at"])
                    if payload.get("last_wrong_at")
                    else None
                ),
            )
            for question_key, payload in attempts_payload.items()
        }

    def _deserialize_cached_recently_correct(
        self, snapshot: dict | None
    ) -> dict[str, datetime]:
        if snapshot is None:
            return {}
        return {
            question_key: datetime.fromisoformat(timestamp)
            for question_key, timestamp in (
                snapshot.get("recently_correct_at_by_question") or {}
            ).items()
            if timestamp
        }

    def _deserialize_cached_attempted_question_ids(
        self, snapshot: dict | None
    ) -> set[str]:
        if snapshot is None:
            return set()
        return {str(value) for value in (snapshot.get("attempted_question_ids") or [])}

    def _deserialize_cached_srs(self, snapshot: dict | None) -> dict[str, SrsState]:
        if snapshot is None:
            return {}
        srs_payload = snapshot.get("srs_by_question") or {}
        return {
            question_key: SrsState(
                box=int(payload.get("box", 0) or 0),
                last_presented_at=(
                    datetime.fromisoformat(payload["last_presented_at"])
                    if payload.get("last_presented_at")
                    else None
                ),
                last_correct_at=(
                    datetime.fromisoformat(payload["last_correct_at"])
                    if payload.get("last_correct_at")
                    else None
                ),
                last_transition_at=(
                    datetime.fromisoformat(payload["last_transition_at"])
                    if payload.get("last_transition_at")
                    else None
                ),
            )
            for question_key, payload in srs_payload.items()
        }

    def _attempt_summary(self, value: Any) -> AttemptHistorySummary:
        if hasattr(value, "total_attempts") and hasattr(value, "wrong_attempts"):
            return AttemptHistorySummary(
                total_attempts=int(getattr(value, "total_attempts", 0) or 0),
                wrong_attempts=int(getattr(value, "wrong_attempts", 0) or 0),
                last_wrong_at=getattr(value, "last_wrong_at", None),
            )

        attempts = list(value or ())
        wrong_timestamps = [
            getattr(attempt, "created_at", None)
            for attempt in attempts
            if not getattr(attempt, "is_correct", False)
            and getattr(attempt, "created_at", None) is not None
        ]
        return AttemptHistorySummary(
            total_attempts=len(attempts),
            wrong_attempts=sum(1 for attempt in attempts if not getattr(attempt, "is_correct", False)),
            last_wrong_at=max(wrong_timestamps) if wrong_timestamps else None,
        )

    def _has_attempt_history(self, value: Any) -> bool:
        return self._attempt_summary(value).total_attempts > 0
