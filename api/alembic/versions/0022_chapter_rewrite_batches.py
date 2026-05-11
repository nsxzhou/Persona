"""add chapter rewrite batches

Revision ID: 0022_chapter_rewrite_batches
Revises: 0021_project_origin
Create Date: 2026-05-11 10:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_chapter_rewrite_batches"
down_revision = "0021_project_origin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chapter_rewrite_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("generated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("applied_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chapter_rewrite_batches_project_id",
        "chapter_rewrite_batches",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batches_project_status",
        "chapter_rewrite_batches",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batches_status",
        "chapter_rewrite_batches",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batches_status_created_at",
        "chapter_rewrite_batches",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batches_status_last_heartbeat_at",
        "chapter_rewrite_batches",
        ["status", "last_heartbeat_at"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batches_user_id",
        "chapter_rewrite_batches",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "chapter_rewrite_batch_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("chapter_id", sa.String(length=36), nullable=False),
        sa.Column("child_run_id", sa.String(length=36), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["chapter_rewrite_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["project_chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_run_id"], ["novel_workflow_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "chapter_id", name="uq_chapter_rewrite_batch_item_chapter"),
        sa.UniqueConstraint("batch_id", "position", name="uq_chapter_rewrite_batch_item_position"),
    )
    op.create_index(
        "ix_chapter_rewrite_batch_items_batch_id",
        "chapter_rewrite_batch_items",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batch_items_batch_status",
        "chapter_rewrite_batch_items",
        ["batch_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batch_items_chapter_id",
        "chapter_rewrite_batch_items",
        ["chapter_id"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batch_items_child_run_id",
        "chapter_rewrite_batch_items",
        ["child_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_chapter_rewrite_batch_items_status",
        "chapter_rewrite_batch_items",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chapter_rewrite_batch_items_status", table_name="chapter_rewrite_batch_items")
    op.drop_index("ix_chapter_rewrite_batch_items_child_run_id", table_name="chapter_rewrite_batch_items")
    op.drop_index("ix_chapter_rewrite_batch_items_chapter_id", table_name="chapter_rewrite_batch_items")
    op.drop_index("ix_chapter_rewrite_batch_items_batch_status", table_name="chapter_rewrite_batch_items")
    op.drop_index("ix_chapter_rewrite_batch_items_batch_id", table_name="chapter_rewrite_batch_items")
    op.drop_table("chapter_rewrite_batch_items")
    op.drop_index("ix_chapter_rewrite_batches_user_id", table_name="chapter_rewrite_batches")
    op.drop_index("ix_chapter_rewrite_batches_status_last_heartbeat_at", table_name="chapter_rewrite_batches")
    op.drop_index("ix_chapter_rewrite_batches_status_created_at", table_name="chapter_rewrite_batches")
    op.drop_index("ix_chapter_rewrite_batches_status", table_name="chapter_rewrite_batches")
    op.drop_index("ix_chapter_rewrite_batches_project_status", table_name="chapter_rewrite_batches")
    op.drop_index("ix_chapter_rewrite_batches_project_id", table_name="chapter_rewrite_batches")
    op.drop_table("chapter_rewrite_batches")
