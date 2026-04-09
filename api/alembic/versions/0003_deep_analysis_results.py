"""deep analysis result payloads

Revision ID: 0003_deep_analysis_results
Revises: 0002_style_lab
Create Date: 2026-04-09 16:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_deep_analysis_results"
down_revision = "0002_style_lab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.add_column(sa.Column("analysis_meta_payload", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("analysis_report_payload", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("style_summary_payload", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("prompt_pack_payload", sa.JSON(), nullable=True))

    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.add_column(sa.Column("analysis_report_payload", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("style_summary_payload", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("prompt_pack_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.drop_column("prompt_pack_payload")
        batch_op.drop_column("style_summary_payload")
        batch_op.drop_column("analysis_report_payload")

    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.drop_column("prompt_pack_payload")
        batch_op.drop_column("style_summary_payload")
        batch_op.drop_column("analysis_report_payload")
        batch_op.drop_column("analysis_meta_payload")
