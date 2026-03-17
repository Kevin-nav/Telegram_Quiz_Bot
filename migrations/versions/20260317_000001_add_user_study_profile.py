"""add user study profile fields

Revision ID: 20260317_000001
Revises: 20260316_000001
Create Date: 2026-03-17 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260317_000001"
down_revision = "20260316_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("faculty_code", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("program_code", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("level_code", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("semester_code", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column("preferred_course_code", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("users", "onboarding_completed", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "preferred_course_code")
    op.drop_column("users", "semester_code")
    op.drop_column("users", "level_code")
    op.drop_column("users", "program_code")
    op.drop_column("users", "faculty_code")
