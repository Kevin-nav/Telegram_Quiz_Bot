from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class QuestionReport(Base):
    __tablename__ = "question_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    bot_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    question_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("question_bank.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    question_index: Mapped[int] = mapped_column(BigInteger, nullable=False)
    report_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    report_reason: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    report_note: Mapped[str | None] = mapped_column(String, nullable=True)
    report_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open", server_default="open", index=True
    )
    report_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
