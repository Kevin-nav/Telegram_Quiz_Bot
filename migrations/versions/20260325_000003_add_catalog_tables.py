"""Add catalog tables

Revision ID: 20260325_000003
Revises: 20260325_000002
Create Date: 2026-03-25 00:00:03.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_000003"
down_revision = "20260325_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_faculties",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_catalog_faculties_code"), "catalog_faculties", ["code"], unique=True)

    op.create_table(
        "catalog_levels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_catalog_levels_code"), "catalog_levels", ["code"], unique=True)

    op.create_table(
        "catalog_semesters",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_catalog_semesters_code"), "catalog_semesters", ["code"], unique=True)

    op.create_table(
        "catalog_courses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_catalog_courses_code"), "catalog_courses", ["code"], unique=True)

    op.create_table(
        "catalog_programs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("faculty_code", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["faculty_code"], ["catalog_faculties.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_catalog_programs_code"), "catalog_programs", ["code"], unique=True)
    op.create_index(op.f("ix_catalog_programs_faculty_code"), "catalog_programs", ["faculty_code"], unique=False)

    op.create_table(
        "program_course_offerings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("program_code", sa.String(length=128), nullable=False),
        sa.Column("level_code", sa.String(length=32), nullable=False),
        sa.Column("semester_code", sa.String(length=32), nullable=False),
        sa.Column("course_code", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_code"], ["catalog_courses.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["level_code"], ["catalog_levels.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["program_code"], ["catalog_programs.code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["semester_code"], ["catalog_semesters.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_code", "level_code", "semester_code", "course_code"),
    )
    op.create_index(
        op.f("ix_program_course_offerings_course_code"),
        "program_course_offerings",
        ["course_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_course_offerings_level_code"),
        "program_course_offerings",
        ["level_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_course_offerings_program_code"),
        "program_course_offerings",
        ["program_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_course_offerings_semester_code"),
        "program_course_offerings",
        ["semester_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_program_course_offerings_semester_code"),
        table_name="program_course_offerings",
    )
    op.drop_index(
        op.f("ix_program_course_offerings_program_code"),
        table_name="program_course_offerings",
    )
    op.drop_index(
        op.f("ix_program_course_offerings_level_code"),
        table_name="program_course_offerings",
    )
    op.drop_index(
        op.f("ix_program_course_offerings_course_code"),
        table_name="program_course_offerings",
    )
    op.drop_table("program_course_offerings")

    op.drop_index(op.f("ix_catalog_programs_faculty_code"), table_name="catalog_programs")
    op.drop_index(op.f("ix_catalog_programs_code"), table_name="catalog_programs")
    op.drop_table("catalog_programs")

    op.drop_index(op.f("ix_catalog_courses_code"), table_name="catalog_courses")
    op.drop_table("catalog_courses")

    op.drop_index(op.f("ix_catalog_semesters_code"), table_name="catalog_semesters")
    op.drop_table("catalog_semesters")

    op.drop_index(op.f("ix_catalog_levels_code"), table_name="catalog_levels")
    op.drop_table("catalog_levels")

    op.drop_index(op.f("ix_catalog_faculties_code"), table_name="catalog_faculties")
    op.drop_table("catalog_faculties")
