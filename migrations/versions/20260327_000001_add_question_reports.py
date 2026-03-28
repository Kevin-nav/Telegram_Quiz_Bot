"""Add question reports

Revision ID: 20260327_000001
Revises: 20260325_000003
Create Date: 2026-03-27 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_000001"
down_revision = "20260325_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=True),
        sa.Column("question_key", sa.String(length=255), nullable=False),
        sa.Column("question_index", sa.BigInteger(), nullable=False),
        sa.Column("report_scope", sa.String(length=32), nullable=False),
        sa.Column("report_reason", sa.String(length=128), nullable=False),
        sa.Column("report_note", sa.String(), nullable=True),
        sa.Column("report_status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["question_bank.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_reports_course_id"), "question_reports", ["course_id"], unique=False)
    op.create_index(op.f("ix_question_reports_question_id"), "question_reports", ["question_id"], unique=False)
    op.create_index(op.f("ix_question_reports_question_key"), "question_reports", ["question_key"], unique=False)
    op.create_index(op.f("ix_question_reports_report_reason"), "question_reports", ["report_reason"], unique=False)
    op.create_index(op.f("ix_question_reports_report_scope"), "question_reports", ["report_scope"], unique=False)
    op.create_index(op.f("ix_question_reports_report_status"), "question_reports", ["report_status"], unique=False)
    op.create_index(op.f("ix_question_reports_session_id"), "question_reports", ["session_id"], unique=False)
    op.create_index(op.f("ix_question_reports_user_id"), "question_reports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_question_reports_user_id"), table_name="question_reports")
    op.drop_index(op.f("ix_question_reports_session_id"), table_name="question_reports")
    op.drop_index(op.f("ix_question_reports_report_status"), table_name="question_reports")
    op.drop_index(op.f("ix_question_reports_report_scope"), table_name="question_reports")
    op.drop_index(op.f("ix_question_reports_report_reason"), table_name="question_reports")
    op.drop_index(op.f("ix_question_reports_question_key"), table_name="question_reports")
    op.drop_index(op.f("ix_question_reports_question_id"), table_name="question_reports")
    op.drop_index(op.f("ix_question_reports_course_id"), table_name="question_reports")
    op.drop_table("question_reports")
