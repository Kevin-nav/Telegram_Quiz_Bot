"""Add denormalized learner metrics

Revision ID: 20260408_000002
Revises: 20260408_000001
Create Date: 2026-04-08 00:00:02.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260408_000002"
down_revision = "20260408_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_course_state",
        sa.Column("total_correct", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "student_course_state",
        sa.Column("avg_time_per_question", sa.Float(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_active_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "longest_streak")
    op.drop_column("users", "current_streak")
    op.drop_column("users", "last_active_date")
    op.drop_column("users", "last_active_at")
    op.drop_column("student_course_state", "avg_time_per_question")
    op.drop_column("student_course_state", "total_correct")
