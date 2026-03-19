"""restore user onboarding_completed default

Revision ID: 20260317_000002
Revises: 20260317_000001
Create Date: 2026-03-17 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260317_000002"
down_revision = "20260317_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "onboarding_completed",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "onboarding_completed",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=None,
    )
