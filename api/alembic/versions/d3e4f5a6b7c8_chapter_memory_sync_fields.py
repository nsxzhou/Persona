"""add chapter memory sync fields

Revision ID: d3e4f5a6b7c8
Revises: c1d2e3f4a5b6
Create Date: 2026-04-17 15:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d3e4f5a6b7c8"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_scope", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_checked_content_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_proposed_state", sa.Text(), nullable=True),
    )
    op.add_column(
        "project_chapters",
        sa.Column("memory_sync_proposed_threads", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_chapters", "memory_sync_proposed_threads")
    op.drop_column("project_chapters", "memory_sync_proposed_state")
    op.drop_column("project_chapters", "memory_sync_error_message")
    op.drop_column("project_chapters", "memory_sync_checked_content_hash")
    op.drop_column("project_chapters", "memory_sync_checked_at")
    op.drop_column("project_chapters", "memory_sync_scope")
    op.drop_column("project_chapters", "memory_sync_source")
    op.drop_column("project_chapters", "memory_sync_status")
