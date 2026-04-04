"""Add admin auth tables

Revision ID: 20260326_000001
Revises: 20260325_000003
Create Date: 2026-03-26 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260326_000001"
down_revision = "20260325_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staff_users",
        sa.Column("password_hash", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "staff_users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
    )
    op.add_column(
        "staff_users",
        sa.Column("password_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "staff_users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("staff_user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["staff_user_id"], ["staff_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token_hash"),
    )
    op.create_index(
        op.f("ix_admin_sessions_session_token_hash"),
        "admin_sessions",
        ["session_token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_admin_sessions_staff_user_id"),
        "admin_sessions",
        ["staff_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_admin_sessions_staff_user_id"),
        table_name="admin_sessions",
    )
    op.drop_index(
        op.f("ix_admin_sessions_session_token_hash"),
        table_name="admin_sessions",
    )
    op.drop_table("admin_sessions")
    op.drop_column("staff_users", "last_login_at")
    op.drop_column("staff_users", "password_updated_at")
    op.drop_column("staff_users", "must_change_password")
    op.drop_column("staff_users", "password_hash")
