"""plot skeleton payload

Revision ID: 0013_plot_skeleton_payload
Revises: 0012_plot_lab
Create Date: 2026-04-21 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_plot_skeleton_payload"
down_revision = "0012_plot_lab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plot_analysis_jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plot_skeleton_payload", sa.Text(), nullable=True))

    with op.batch_alter_table("plot_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plot_skeleton_payload", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("plot_profiles", schema=None) as batch_op:
        batch_op.drop_column("plot_skeleton_payload")

    with op.batch_alter_table("plot_analysis_jobs", schema=None) as batch_op:
        batch_op.drop_column("plot_skeleton_payload")
