from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.base import Base


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    course_slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(String, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    correct_option_text: Mapped[str] = mapped_column(String, nullable=False)
    short_explanation: Mapped[str | None] = mapped_column(String, nullable=True)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False, default="MCQ")
    option_count: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    has_latex: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    scaled_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    base_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    band: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cognitive_level: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    processing_complexity: Mapped[float | None] = mapped_column(Float, nullable=True)
    distractor_complexity: Mapped[float | None] = mapped_column(Float, nullable=True)
    note_reference: Mapped[float | None] = mapped_column(Float, nullable=True)
    negative_stem: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    render_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    explanation_asset_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    explanation_asset_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    variant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", server_default="draft", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    asset_variants: Mapped[list["QuestionAssetVariant"]] = relationship(
        "QuestionAssetVariant",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="QuestionAssetVariant.variant_index.asc()",
    )
