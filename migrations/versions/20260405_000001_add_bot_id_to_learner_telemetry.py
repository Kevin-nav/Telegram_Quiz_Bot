"""Add bot_id to learner telemetry tables

Revision ID: 20260405_000001
Revises: 20260404_000003
Create Date: 2026-04-05 00:00:01.000000
"""

from __future__ import annotations

from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision = "20260405_000001"
down_revision = "20260404_000003"
branch_labels = None
depends_on = None

UNKNOWN_BOT_ID = "unknown"


def _load_course_to_bots() -> dict[str, set[str]]:
    from src.core.config import settings

    course_to_bots: dict[str, set[str]] = defaultdict(set)
    for bot_id, bot_config in settings.bot_configs.items():
        allowed_course_codes = tuple(getattr(bot_config, "allowed_course_codes", ()) or ())
        if not allowed_course_codes:
            continue
        for course_code in allowed_course_codes:
            course_to_bots[str(course_code)].add(bot_id)
    return course_to_bots


def _resolve_bot_id(course_code: str | None, course_to_bots: dict[str, set[str]]) -> str:
    if not course_code:
        return UNKNOWN_BOT_ID

    bot_ids = course_to_bots.get(str(course_code), set())
    if len(bot_ids) == 1:
        return next(iter(bot_ids))
    return UNKNOWN_BOT_ID


def _find_unique_constraint_name(bind, table_name: str, columns: tuple[str, ...]) -> str:
    inspector = sa.inspect(bind)
    for constraint in inspector.get_unique_constraints(table_name):
        if tuple(constraint.get("column_names") or ()) == columns:
            constraint_name = constraint.get("name")
            if constraint_name:
                return constraint_name
    raise RuntimeError(f"Unable to find unique constraint for {table_name} on {columns!r}.")


def _backfill_course_scoped_table(
    bind,
    *,
    table_name: str,
    course_column: str = "course_id",
    course_to_bots: dict[str, set[str]],
) -> None:
    table = sa.table(
        table_name,
        sa.column("id", sa.BigInteger()),
        sa.column(course_column, sa.String(length=128)),
        sa.column("bot_id", sa.String(length=32)),
    )
    course_col = getattr(table.c, course_column)
    distinct_course_rows = bind.execute(
        sa.select(sa.distinct(course_col)).where(table.c.bot_id.is_(None))
    ).all()

    course_ids_by_bot: dict[str, list[str]] = defaultdict(list)
    for row in distinct_course_rows:
        course_code = row[0]
        if course_code is None:
            continue
        course_ids_by_bot[_resolve_bot_id(str(course_code), course_to_bots)].append(
            str(course_code)
        )

    for bot_id, course_codes in course_ids_by_bot.items():
        if not course_codes:
            continue
        bind.execute(
            sa.update(table)
            .where(course_col.in_(course_codes))
            .where(table.c.bot_id.is_(None))
            .values(bot_id=bot_id)
        )
    bind.execute(
        sa.update(table)
        .where(table.c.bot_id.is_(None))
        .values(bot_id=UNKNOWN_BOT_ID)
    )


def _backfill_analytics_events(bind, *, course_to_bots: dict[str, set[str]]) -> None:
    table = sa.table(
        "analytics_events",
        sa.column("id", sa.BigInteger()),
        sa.column("metadata", sa.JSON()),
        sa.column("bot_id", sa.String(length=32)),
    )
    rows = bind.execute(
        sa.select(table.c.id, table.c.metadata).where(table.c.bot_id.is_(None))
    ).all()

    ids_by_bot: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        metadata = row[1] if isinstance(row[1], dict) else {}
        course_code = metadata.get("course_id") if isinstance(metadata, dict) else None
        ids_by_bot[_resolve_bot_id(str(course_code).strip() if course_code else None, course_to_bots)].append(
            row[0]
        )

    for bot_id, ids in ids_by_bot.items():
        if not ids:
            continue
        bind.execute(
            sa.update(table)
            .where(table.c.id.in_(ids))
            .where(table.c.bot_id.is_(None))
            .values(bot_id=bot_id)
        )
    bind.execute(
        sa.update(table)
        .where(table.c.bot_id.is_(None))
        .values(bot_id=UNKNOWN_BOT_ID)
    )


def upgrade() -> None:
    op.add_column(
        "question_attempts",
        sa.Column("bot_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "question_reports",
        sa.Column("bot_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "student_course_state",
        sa.Column("bot_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "student_question_srs",
        sa.Column("bot_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "analytics_events",
        sa.Column("bot_id", sa.String(length=32), nullable=True),
    )

    bind = op.get_bind()
    course_to_bots = _load_course_to_bots()

    _backfill_course_scoped_table(
        bind,
        table_name="question_attempts",
        course_to_bots=course_to_bots,
    )
    _backfill_course_scoped_table(
        bind,
        table_name="question_reports",
        course_to_bots=course_to_bots,
    )
    _backfill_course_scoped_table(
        bind,
        table_name="student_course_state",
        course_to_bots=course_to_bots,
    )
    _backfill_course_scoped_table(
        bind,
        table_name="student_question_srs",
        course_to_bots=course_to_bots,
    )
    _backfill_analytics_events(bind, course_to_bots=course_to_bots)

    old_constraint_name = _find_unique_constraint_name(
        bind,
        "student_course_state",
        ("user_id", "course_id"),
    )
    op.drop_constraint(old_constraint_name, "student_course_state", type_="unique")
    op.create_unique_constraint(
        "uq_student_course_state_user_course_bot",
        "student_course_state",
        ["user_id", "course_id", "bot_id"],
    )

    old_constraint_name = _find_unique_constraint_name(
        bind,
        "student_question_srs",
        ("user_id", "question_id"),
    )
    op.drop_constraint(old_constraint_name, "student_question_srs", type_="unique")
    op.create_unique_constraint(
        "uq_student_question_srs_user_question_bot",
        "student_question_srs",
        ["user_id", "question_id", "bot_id"],
    )

    op.create_index(
        op.f("ix_question_attempts_bot_id"),
        "question_attempts",
        ["bot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_reports_bot_id"),
        "question_reports",
        ["bot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_course_state_bot_id"),
        "student_course_state",
        ["bot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_question_srs_bot_id"),
        "student_question_srs",
        ["bot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analytics_events_bot_id"),
        "analytics_events",
        ["bot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analytics_events_bot_id"), table_name="analytics_events")
    op.drop_index(op.f("ix_student_question_srs_bot_id"), table_name="student_question_srs")
    op.drop_index(op.f("ix_student_course_state_bot_id"), table_name="student_course_state")
    op.drop_index(op.f("ix_question_reports_bot_id"), table_name="question_reports")
    op.drop_index(op.f("ix_question_attempts_bot_id"), table_name="question_attempts")

    bind = op.get_bind()

    old_constraint_name = _find_unique_constraint_name(
        bind,
        "student_question_srs",
        ("user_id", "question_id", "bot_id"),
    )
    op.drop_constraint(old_constraint_name, "student_question_srs", type_="unique")
    op.create_unique_constraint(
        "student_question_srs_user_id_question_id_key",
        "student_question_srs",
        ["user_id", "question_id"],
    )

    old_constraint_name = _find_unique_constraint_name(
        bind,
        "student_course_state",
        ("user_id", "course_id", "bot_id"),
    )
    op.drop_constraint(old_constraint_name, "student_course_state", type_="unique")
    op.create_unique_constraint(
        "student_course_state_user_id_course_id_key",
        "student_course_state",
        ["user_id", "course_id"],
    )

    op.drop_column("analytics_events", "bot_id")
    op.drop_column("student_question_srs", "bot_id")
    op.drop_column("student_course_state", "bot_id")
    op.drop_column("question_reports", "bot_id")
    op.drop_column("question_attempts", "bot_id")
