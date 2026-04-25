"""add generation profile payload

Revision ID: 0015_gen_profile_payload
Revises: 0014_analysis_stage_renames
Create Date: 2026-04-25 22:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_gen_profile_payload"
down_revision = "0014_analysis_stage_renames"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("generation_profile_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("generation_profile_payload")
