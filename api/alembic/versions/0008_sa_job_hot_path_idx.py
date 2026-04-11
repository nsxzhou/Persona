"""style analysis job hot path indexes

Revision ID: 0008_sa_job_hot_path_idx
Revises: 0007_style_analysis_job_indexes
Create Date: 2026-04-11 00:00:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "0008_sa_job_hot_path_idx"
down_revision = "0007_style_analysis_job_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.create_index(
            "ix_style_analysis_jobs_status_attempt_count_created_at",
            ["status", "attempt_count", "created_at"],
        )
        batch_op.create_index(
            "ix_style_analysis_jobs_status_last_heartbeat_at",
            ["status", "last_heartbeat_at"],
        )


def downgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.drop_index("ix_style_analysis_jobs_status_last_heartbeat_at")
        batch_op.drop_index("ix_style_analysis_jobs_status_attempt_count_created_at")
