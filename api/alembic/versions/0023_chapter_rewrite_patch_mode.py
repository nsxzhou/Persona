"""add chapter rewrite expansion ratio

Revision ID: 0023_chapter_rewrite_patch_mode
Revises: 0022_chapter_rewrite_batches
Create Date: 2026-05-11 14:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023_chapter_rewrite_patch_mode"
down_revision = "0022_chapter_rewrite_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("chapter_rewrite_batches", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "expansion_ratio_percent",
                sa.Integer(),
                nullable=False,
                server_default="20",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("chapter_rewrite_batches", schema=None) as batch_op:
        batch_op.drop_column("expansion_ratio_percent")
