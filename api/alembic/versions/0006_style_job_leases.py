"""style job leases

Revision ID: 0006_style_job_leases
Revises: 0005_remove_style_job_draft
Create Date: 2026-04-10 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_style_job_leases"
down_revision = "0005_remove_style_job_draft"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.add_column(sa.Column("locked_by", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "attempt_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.drop_column("attempt_count")
        batch_op.drop_column("last_heartbeat_at")
        batch_op.drop_column("locked_at")
        batch_op.drop_column("locked_by")
