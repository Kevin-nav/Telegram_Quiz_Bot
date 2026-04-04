"""Add staff bot and catalog access tables

Revision ID: 20260404_000003
Revises: 20260404_000002
Create Date: 2026-04-04 00:00:03.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_000003"
down_revision = "20260404_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staff_users",
        sa.Column("last_selected_bot_id", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "staff_bot_access",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("staff_user_id", sa.BigInteger(), nullable=False),
        sa.Column("bot_id", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["staff_user_id"],
            ["staff_users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_user_id", "bot_id"),
    )
    op.create_index(
        op.f("ix_staff_bot_access_bot_id"),
        "staff_bot_access",
        ["bot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_bot_access_staff_user_id"),
        "staff_bot_access",
        ["staff_user_id"],
        unique=False,
    )

    op.create_table(
        "staff_catalog_access",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("staff_user_id", sa.BigInteger(), nullable=False),
        sa.Column("bot_id", sa.String(length=32), nullable=False),
        sa.Column("program_code", sa.String(length=128), nullable=True),
        sa.Column("level_code", sa.String(length=32), nullable=True),
        sa.Column("course_code", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_code"],
            ["catalog_courses.code"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["level_code"],
            ["catalog_levels.code"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_code"],
            ["catalog_programs.code"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["staff_user_id"],
            ["staff_users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "staff_user_id",
            "bot_id",
            "program_code",
            "level_code",
            "course_code",
        ),
    )
    op.create_index(
        op.f("ix_staff_catalog_access_bot_id"),
        "staff_catalog_access",
        ["bot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_catalog_access_course_code"),
        "staff_catalog_access",
        ["course_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_catalog_access_level_code"),
        "staff_catalog_access",
        ["level_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_catalog_access_program_code"),
        "staff_catalog_access",
        ["program_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_catalog_access_staff_user_id"),
        "staff_catalog_access",
        ["staff_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_staff_catalog_access_staff_user_id"),
        table_name="staff_catalog_access",
    )
    op.drop_index(
        op.f("ix_staff_catalog_access_program_code"),
        table_name="staff_catalog_access",
    )
    op.drop_index(
        op.f("ix_staff_catalog_access_level_code"),
        table_name="staff_catalog_access",
    )
    op.drop_index(
        op.f("ix_staff_catalog_access_course_code"),
        table_name="staff_catalog_access",
    )
    op.drop_index(
        op.f("ix_staff_catalog_access_bot_id"),
        table_name="staff_catalog_access",
    )
    op.drop_table("staff_catalog_access")
    op.drop_index(
        op.f("ix_staff_bot_access_staff_user_id"),
        table_name="staff_bot_access",
    )
    op.drop_index(
        op.f("ix_staff_bot_access_bot_id"),
        table_name="staff_bot_access",
    )
    op.drop_table("staff_bot_access")
    op.drop_column("staff_users", "last_selected_bot_id")
