"""style job pause

Revision ID: 0011_style_job_pause
Revises: 0010_markdown_style_lab_payloads
Create Date: 2026-04-13 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0011_style_job_pause"
down_revision = "0010_markdown_style_lab_payloads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("pause_requested_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.drop_column("paused_at")
        batch_op.drop_column("pause_requested_at")

