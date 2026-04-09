"""remove style job draft payload

Revision ID: 0005_remove_style_job_draft
Revises: 0004_style_profiles_payload_only
Create Date: 2026-04-09 22:25:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_remove_style_job_draft"
down_revision = "0004_style_profiles_payload_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.drop_column("draft_payload")


def downgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.add_column(sa.Column("draft_payload", sa.JSON(), nullable=True))
