from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.base import Base


class QuestionAssetVariant(Base):
    __tablename__ = "question_asset_variants"
    __table_args__ = (UniqueConstraint("question_id", "variant_index"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False
    )
    variant_index: Mapped[int] = mapped_column(Integer, nullable=False)
    option_order: Mapped[list[int]] = mapped_column(JSON, default=list)
    question_asset_key: Mapped[str] = mapped_column(String(512), nullable=False)
    question_asset_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    render_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
