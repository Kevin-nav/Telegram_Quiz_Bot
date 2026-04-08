"""Add student session summary table

Revision ID: 20260408_000003
Revises: 20260408_000002
Create Date: 2026-04-08 00:00:03.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260408_000003"
down_revision = "20260408_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_session_summary",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("bot_id", sa.String(length=32), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accuracy_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_time_seconds", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "bot_id",
            name="uq_student_session_summary_session_bot",
        ),
    )
    op.create_index(
        "ix_student_session_summary_session_id",
        "student_session_summary",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_student_session_summary_user_id",
        "student_session_summary",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_student_session_summary_course_id",
        "student_session_summary",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        "ix_student_session_summary_bot_id",
        "student_session_summary",
        ["bot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_student_session_summary_bot_id", table_name="student_session_summary")
    op.drop_index("ix_student_session_summary_course_id", table_name="student_session_summary")
    op.drop_index("ix_student_session_summary_user_id", table_name="student_session_summary")
    op.drop_index("ix_student_session_summary_session_id", table_name="student_session_summary")
    op.drop_table("student_session_summary")
