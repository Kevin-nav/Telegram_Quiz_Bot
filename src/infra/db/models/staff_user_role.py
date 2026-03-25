from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class StaffUserRole(Base):
    __tablename__ = "staff_user_roles"
    __table_args__ = (UniqueConstraint("staff_user_id", "staff_role_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    staff_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("staff_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    staff_role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("staff_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
