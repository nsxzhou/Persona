"""add chapter summary

Revision ID: 1000_add_chapter_summary
Revises: 0015_gen_profile_payload, f5a6b7c8d9e0
Create Date: 2026-04-27 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "1000_add_chapter_summary"
down_revision = ("0015_gen_profile_payload", "f5a6b7c8d9e0")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_chapters", sa.Column("summary", sa.Text(), nullable=False, server_default=""))
    op.add_column("project_chapters", sa.Column("memory_sync_proposed_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_chapters", "memory_sync_proposed_summary")
    op.drop_column("project_chapters", "summary")