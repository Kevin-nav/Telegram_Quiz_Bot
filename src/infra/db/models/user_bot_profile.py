from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class UserBotProfile(Base):
    __tablename__ = "user_bot_profiles"
    __table_args__ = (UniqueConstraint("user_id", "bot_id", name="uq_user_bot_profiles_user_bot"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    faculty_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    program_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    level_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    semester_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_course_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
