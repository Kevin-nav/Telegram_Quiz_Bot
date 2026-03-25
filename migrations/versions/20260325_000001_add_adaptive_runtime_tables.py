"""Add adaptive runtime tables

Revision ID: 20260325_000001
Revises: fce94d47f96b
Create Date: 2026-03-25 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_000001"
down_revision = "fce94d47f96b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_question_srs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("box", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_presented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_correct_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transition_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["question_bank.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id"),
    )
    op.create_index(
        op.f("ix_student_question_srs_course_id"),
        "student_question_srs",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_question_srs_question_id"),
        "student_question_srs",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_question_srs_user_id"),
        "student_question_srs",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "adaptive_review_flags",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("suggestion", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["question_id"], ["question_bank.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_adaptive_review_flags_flag_type"),
        "adaptive_review_flags",
        ["flag_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adaptive_review_flags_question_id"),
        "adaptive_review_flags",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adaptive_review_flags_status"),
        "adaptive_review_flags",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_adaptive_review_flags_status"), table_name="adaptive_review_flags")
    op.drop_index(op.f("ix_adaptive_review_flags_question_id"), table_name="adaptive_review_flags")
    op.drop_index(op.f("ix_adaptive_review_flags_flag_type"), table_name="adaptive_review_flags")
    op.drop_table("adaptive_review_flags")

    op.drop_index(op.f("ix_student_question_srs_user_id"), table_name="student_question_srs")
    op.drop_index(op.f("ix_student_question_srs_question_id"), table_name="student_question_srs")
    op.drop_index(op.f("ix_student_question_srs_course_id"), table_name="student_question_srs")
    op.drop_table("student_question_srs")
