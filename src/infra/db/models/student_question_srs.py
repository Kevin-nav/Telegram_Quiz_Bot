from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class StudentQuestionSrs(Base):
    __tablename__ = "student_question_srs"
    __table_args__ = (UniqueConstraint("user_id", "question_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False, index=True
    )
    box: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_presented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_correct_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_transition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
