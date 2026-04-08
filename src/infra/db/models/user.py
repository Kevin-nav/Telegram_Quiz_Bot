from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    faculty_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    program_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    level_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    semester_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_course_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    longest_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
