from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class StudentCourseState(Base):
    __tablename__ = "student_course_state"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "course_id",
            "bot_id",
            name="uq_student_course_state_user_course_bot",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    bot_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    overall_skill: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5, server_default="2.5"
    )
    topic_skills: Mapped[dict] = mapped_column(JSON, default=dict)
    cognitive_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    processing_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    misconception_flags: Mapped[list[dict]] = mapped_column(JSON, default=list)
    phase: Mapped[str] = mapped_column(
        String(32), nullable=False, default="cold_start", server_default="cold_start"
    )
    total_quizzes_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    total_correct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    avg_time_per_question: Mapped[float | None] = mapped_column(Float, nullable=True)
    exam_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
