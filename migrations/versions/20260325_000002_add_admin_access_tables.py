"""Add admin access tables

Revision ID: 20260325_000002
Revises: 20260325_000001
Create Date: 2026-03-25 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_000002"
down_revision = "20260325_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staff_users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_staff_users_email"), "staff_users", ["email"], unique=True)

    op.create_table(
        "staff_roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_staff_roles_code"), "staff_roles", ["code"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_permissions_code"), "permissions", ["code"], unique=True)

    op.create_table(
        "staff_user_roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("staff_user_id", sa.BigInteger(), nullable=False),
        sa.Column("staff_role_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["staff_role_id"], ["staff_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_user_id"], ["staff_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_user_id", "staff_role_id"),
    )
    op.create_index(op.f("ix_staff_user_roles_staff_role_id"), "staff_user_roles", ["staff_role_id"], unique=False)
    op.create_index(op.f("ix_staff_user_roles_staff_user_id"), "staff_user_roles", ["staff_user_id"], unique=False)

    op.create_table(
        "staff_user_permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("staff_user_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_user_id"], ["staff_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_user_id", "permission_id"),
    )
    op.create_index(
        op.f("ix_staff_user_permissions_permission_id"),
        "staff_user_permissions",
        ["permission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_user_permissions_staff_user_id"),
        "staff_user_permissions",
        ["staff_user_id"],
        unique=False,
    )

    op.create_table(
        "staff_role_permissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("staff_role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_role_id"], ["staff_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_role_id", "permission_id"),
    )
    op.create_index(
        op.f("ix_staff_role_permissions_permission_id"),
        "staff_role_permissions",
        ["permission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_staff_role_permissions_staff_role_id"),
        "staff_role_permissions",
        ["staff_role_id"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor_staff_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("before_data", sa.JSON(), nullable=True),
        sa.Column("after_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_actor_staff_user_id"),
        "audit_logs",
        ["actor_staff_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_staff_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(
        op.f("ix_staff_role_permissions_staff_role_id"),
        table_name="staff_role_permissions",
    )
    op.drop_index(
        op.f("ix_staff_role_permissions_permission_id"),
        table_name="staff_role_permissions",
    )
    op.drop_table("staff_role_permissions")

    op.drop_index(
        op.f("ix_staff_user_permissions_staff_user_id"),
        table_name="staff_user_permissions",
    )
    op.drop_index(
        op.f("ix_staff_user_permissions_permission_id"),
        table_name="staff_user_permissions",
    )
    op.drop_table("staff_user_permissions")

    op.drop_index(op.f("ix_staff_user_roles_staff_user_id"), table_name="staff_user_roles")
    op.drop_index(op.f("ix_staff_user_roles_staff_role_id"), table_name="staff_user_roles")
    op.drop_table("staff_user_roles")

    op.drop_index(op.f("ix_permissions_code"), table_name="permissions")
    op.drop_table("permissions")

    op.drop_index(op.f("ix_staff_roles_code"), table_name="staff_roles")
    op.drop_table("staff_roles")

    op.drop_index(op.f("ix_staff_users_email"), table_name="staff_users")
    op.drop_table("staff_users")
