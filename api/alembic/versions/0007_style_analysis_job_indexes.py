"""style analysis job indexes

Revision ID: 0007_style_analysis_job_indexes
Revises: 0006_style_job_leases
Create Date: 2026-04-10 00:00:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "0007_style_analysis_job_indexes"
down_revision = "0006_style_job_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.create_index("ix_style_analysis_jobs_status", ["status"])
        batch_op.create_index(
            "ix_style_analysis_jobs_status_created_at",
            ["status", "created_at"],
        )


def downgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.drop_index("ix_style_analysis_jobs_status_created_at")
        batch_op.drop_index("ix_style_analysis_jobs_status")

