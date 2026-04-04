from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class StaffCatalogAccess(Base):
    __tablename__ = "staff_catalog_access"
    __table_args__ = (
        UniqueConstraint(
            "staff_user_id",
            "bot_id",
            "program_code",
            "level_code",
            "course_code",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    staff_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("staff_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    program_code: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("catalog_programs.code", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    level_code: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("catalog_levels.code", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    course_code: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("catalog_courses.code", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
