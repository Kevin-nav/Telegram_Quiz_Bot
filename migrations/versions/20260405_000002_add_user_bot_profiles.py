"""Add bot-scoped learner profiles

Revision ID: 20260405_000002
Revises: 20260405_000001
Create Date: 2026-04-05 00:00:02.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260405_000002"
down_revision = "20260405_000001"
branch_labels = None
depends_on = None


def _iter_profile_bot_ids(bind, user_id: int) -> list[str]:
    candidate_tables = (
        "question_attempts",
        "question_reports",
        "student_course_state",
        "student_question_srs",
        "analytics_events",
    )
    bot_ids: set[str] = set()
    for table_name in candidate_tables:
        rows = bind.execute(
            sa.text(
                f"""
                SELECT DISTINCT bot_id
                FROM {table_name}
                WHERE user_id = :user_id
                  AND bot_id IS NOT NULL
                  AND bot_id <> 'unknown'
                """
            ),
            {"user_id": user_id},
        ).fetchall()
        bot_ids.update(str(row[0]) for row in rows if row[0])
    return sorted(bot_ids)


def upgrade() -> None:
    op.create_table(
        "user_bot_profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bot_id", sa.String(length=32), nullable=False),
        sa.Column("faculty_code", sa.String(length=64), nullable=True),
        sa.Column("program_code", sa.String(length=128), nullable=True),
        sa.Column("level_code", sa.String(length=32), nullable=True),
        sa.Column("semester_code", sa.String(length=32), nullable=True),
        sa.Column("preferred_course_code", sa.String(length=128), nullable=True),
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
        sa.UniqueConstraint("user_id", "bot_id", name="uq_user_bot_profiles_user_bot"),
    )
    op.create_index(
        op.f("ix_user_bot_profiles_user_id"),
        "user_bot_profiles",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_bot_profiles_bot_id"),
        "user_bot_profiles",
        ["bot_id"],
        unique=False,
    )

    bind = op.get_bind()
    users = bind.execute(
        sa.text(
            """
            SELECT
                id,
                faculty_code,
                program_code,
                level_code,
                semester_code,
                preferred_course_code,
                onboarding_completed,
                created_at
            FROM users
            """
        )
    ).mappings()

    insert_stmt = sa.text(
        """
        INSERT INTO user_bot_profiles (
            user_id,
            bot_id,
            faculty_code,
            program_code,
            level_code,
            semester_code,
            preferred_course_code,
            onboarding_completed,
            created_at,
            updated_at
        )
        VALUES (
            :user_id,
            :bot_id,
            :faculty_code,
            :program_code,
            :level_code,
            :semester_code,
            :preferred_course_code,
            :onboarding_completed,
            :created_at,
            :created_at
        )
        """
    )

    for row in users:
        bot_ids = _iter_profile_bot_ids(bind, int(row["id"]))
        if not bot_ids:
            bot_ids = ["tanjah"]
        for bot_id in bot_ids:
            bind.execute(
                insert_stmt,
                {
                    "user_id": row["id"],
                    "bot_id": bot_id,
                    "faculty_code": row["faculty_code"],
                    "program_code": row["program_code"],
                    "level_code": row["level_code"],
                    "semester_code": row["semester_code"],
                    "preferred_course_code": row["preferred_course_code"],
                    "onboarding_completed": bool(row["onboarding_completed"]),
                    "created_at": row["created_at"],
                },
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_bot_profiles_bot_id"), table_name="user_bot_profiles")
    op.drop_index(op.f("ix_user_bot_profiles_user_id"), table_name="user_bot_profiles")
    op.drop_table("user_bot_profiles")
