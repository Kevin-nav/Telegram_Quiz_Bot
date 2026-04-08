"""Add hot path composite indexes

Revision ID: 20260408_000001
Revises: 20260405_000002
Create Date: 2026-04-08 00:00:01.000000
"""

from __future__ import annotations

from alembic import op


revision = "20260408_000001"
down_revision = "20260405_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_question_bank_course_status_id",
        "question_bank",
        ["course_id", "status", "id"],
        unique=False,
    )
    op.create_index(
        "ix_question_attempts_bot_user_created_at",
        "question_attempts",
        ["bot_id", "user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_question_attempts_bot_user_question_created_at",
        "question_attempts",
        ["bot_id", "user_id", "question_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_question_reports_bot_status_created_at",
        "question_reports",
        ["bot_id", "report_status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_program_course_offerings_program_level_semester_active_course",
        "program_course_offerings",
        ["program_code", "level_code", "semester_code", "is_active", "course_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_program_course_offerings_program_level_semester_active_course",
        table_name="program_course_offerings",
    )
    op.drop_index(
        "ix_question_reports_bot_status_created_at",
        table_name="question_reports",
    )
    op.drop_index(
        "ix_question_attempts_bot_user_question_created_at",
        table_name="question_attempts",
    )
    op.drop_index(
        "ix_question_attempts_bot_user_created_at",
        table_name="question_attempts",
    )
    op.drop_index(
        "ix_question_bank_course_status_id",
        table_name="question_bank",
    )
