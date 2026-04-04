"""Add bot-scoped question assets

Revision ID: 20260404_000001
Revises: 20260327_000001
Create Date: 2026-04-04 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_000001"
down_revision = "20260327_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_asset_variants",
        sa.Column(
            "bot_id",
            sa.String(length=32),
            server_default="tanjah",
            nullable=False,
        ),
    )
    op.drop_constraint(
        "question_asset_variants_question_id_variant_index_key",
        "question_asset_variants",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_question_asset_variants_question_bot_variant",
        "question_asset_variants",
        ["question_id", "bot_id", "variant_index"],
    )

    op.add_column(
        "question_bank",
        sa.Column("explanation_asset_keys_by_bot", sa.JSON(), nullable=True),
    )
    op.add_column(
        "question_bank",
        sa.Column("explanation_asset_urls_by_bot", sa.JSON(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE question_bank
            SET explanation_asset_keys_by_bot = json_build_object('tanjah', explanation_asset_key)
            WHERE explanation_asset_key IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE question_bank
            SET explanation_asset_urls_by_bot = json_build_object('tanjah', explanation_asset_url)
            WHERE explanation_asset_url IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("question_bank", "explanation_asset_urls_by_bot")
    op.drop_column("question_bank", "explanation_asset_keys_by_bot")
    op.drop_constraint(
        "uq_question_asset_variants_question_bot_variant",
        "question_asset_variants",
        type_="unique",
    )
    op.create_unique_constraint(
        "question_asset_variants_question_id_variant_index_key",
        "question_asset_variants",
        ["question_id", "variant_index"],
    )
    op.drop_column("question_asset_variants", "bot_id")
