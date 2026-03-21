from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False
    )
    question_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_option_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    selected_option_text: Mapped[str | None] = mapped_column(String, nullable=True)
    correct_option_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    arrangement_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_taken_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_allocated_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
