"""add project prompt assets

Revision ID: 0019_project_prompt_assets
Revises: 0018_provider_prompt_override
Create Date: 2026-05-08 13:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0019_project_prompt_assets"
down_revision = "0018_provider_prompt_override"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_prompt_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("chapter_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("keywords_payload", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("always_on", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["project_chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_prompt_assets_chapter_id",
        "project_prompt_assets",
        ["chapter_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_prompt_assets_project_enabled",
        "project_prompt_assets",
        ["project_id", "enabled"],
        unique=False,
    )
    op.create_index(
        "ix_project_prompt_assets_project_id",
        "project_prompt_assets",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_prompt_assets_project_kind_priority",
        "project_prompt_assets",
        ["project_id", "kind", "priority"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_prompt_assets_project_kind_priority", table_name="project_prompt_assets")
    op.drop_index("ix_project_prompt_assets_project_id", table_name="project_prompt_assets")
    op.drop_index("ix_project_prompt_assets_project_enabled", table_name="project_prompt_assets")
    op.drop_index("ix_project_prompt_assets_chapter_id", table_name="project_prompt_assets")
    op.drop_table("project_prompt_assets")
