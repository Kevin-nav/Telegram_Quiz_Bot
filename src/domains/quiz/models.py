from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class QuizQuestion:
    question_id: str
    prompt: str
    options: list[str]
    correct_option_id: int
    source_question_id: int | None = None
    explanation: str | None = None
    topic_id: str | None = None
    has_latex: bool = False
    arrangement_hash: str | None = None
    config_index: int | None = None
    question_asset_url: str | None = None
    explanation_asset_url: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "QuizQuestion":
        return cls(
            question_id=payload["question_id"],
            source_question_id=payload.get("source_question_id"),
            prompt=payload["prompt"],
            options=list(payload["options"]),
            correct_option_id=payload["correct_option_id"],
            explanation=payload.get("explanation"),
            topic_id=payload.get("topic_id"),
            has_latex=payload.get("has_latex", False),
            arrangement_hash=payload.get("arrangement_hash"),
            config_index=payload.get("config_index"),
            question_asset_url=payload.get("question_asset_url"),
            explanation_asset_url=payload.get("explanation_asset_url"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class QuizSessionState:
    session_id: str
    user_id: int
    chat_id: int
    course_id: str
    course_name: str
    questions: list[QuizQuestion]
    current_index: int = 0
    current_poll_id: str | None = None
    status: str = "active"
    score: int = 0

    @classmethod
    def from_dict(cls, payload: dict) -> "QuizSessionState":
        return cls(
            session_id=payload["session_id"],
            user_id=payload["user_id"],
            chat_id=payload["chat_id"],
            course_id=payload["course_id"],
            course_name=payload["course_name"],
            questions=[
                QuizQuestion.from_dict(question)
                for question in payload.get("questions", [])
            ],
            current_index=payload.get("current_index", 0),
            current_poll_id=payload.get("current_poll_id"),
            status=payload.get("status", "active"),
            score=payload.get("score", 0),
        )

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "course_id": self.course_id,
            "course_name": self.course_name,
            "questions": [question.to_dict() for question in self.questions],
            "current_index": self.current_index,
            "current_poll_id": self.current_poll_id,
            "status": self.status,
            "score": self.score,
        }

    def current_question(self) -> QuizQuestion | None:
        if self.current_index >= len(self.questions):
            return None
        return self.questions[self.current_index]

    @property
    def total_questions(self) -> int:
        return len(self.questions)


@dataclass(slots=True)
class PollMapRecord:
    poll_id: str
    session_id: str
    question_id: str
    question_index: int
    user_id: int

    @classmethod
    def from_dict(cls, payload: dict) -> "PollMapRecord":
        return cls(
            poll_id=payload["poll_id"],
            session_id=payload["session_id"],
            question_id=payload["question_id"],
            question_index=payload["question_index"],
            user_id=payload["user_id"],
        )

    def to_dict(self) -> dict:
        return asdict(self)
