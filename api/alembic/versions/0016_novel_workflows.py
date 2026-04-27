"""add novel workflow tables and fields

Revision ID: 0016_novel_workflows
Revises: f6a7b8c9d0e1
Create Date: 2026-04-27 11:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_novel_workflows"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_bibles",
        sa.Column("story_summary", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "project_chapters",
        sa.Column("beats_markdown", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "novel_workflow_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("chapter_id", sa.String(length=36), nullable=True),
        sa.Column("provider_id", sa.String(length=36), nullable=True),
        sa.Column("intent_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("checkpoint_kind", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("latest_artifacts_payload", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("warnings_payload", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("decision_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chapter_id"], ["project_chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_configs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_novel_workflow_runs_status_created_at",
        "novel_workflow_runs",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_novel_workflow_runs_status_attempt_count_created_at",
        "novel_workflow_runs",
        ["status", "attempt_count", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_novel_workflow_runs_status_last_heartbeat_at",
        "novel_workflow_runs",
        ["status", "last_heartbeat_at"],
        unique=False,
    )
    op.create_index(op.f("ix_novel_workflow_runs_user_id"), "novel_workflow_runs", ["user_id"], unique=False)
    op.create_index(op.f("ix_novel_workflow_runs_project_id"), "novel_workflow_runs", ["project_id"], unique=False)
    op.create_index(op.f("ix_novel_workflow_runs_chapter_id"), "novel_workflow_runs", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_novel_workflow_runs_provider_id"), "novel_workflow_runs", ["provider_id"], unique=False)
    op.create_index(op.f("ix_novel_workflow_runs_intent_type"), "novel_workflow_runs", ["intent_type"], unique=False)
    op.create_index(op.f("ix_novel_workflow_runs_status"), "novel_workflow_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_novel_workflow_runs_status"), table_name="novel_workflow_runs")
    op.drop_index(op.f("ix_novel_workflow_runs_intent_type"), table_name="novel_workflow_runs")
    op.drop_index(op.f("ix_novel_workflow_runs_provider_id"), table_name="novel_workflow_runs")
    op.drop_index(op.f("ix_novel_workflow_runs_chapter_id"), table_name="novel_workflow_runs")
    op.drop_index(op.f("ix_novel_workflow_runs_project_id"), table_name="novel_workflow_runs")
    op.drop_index(op.f("ix_novel_workflow_runs_user_id"), table_name="novel_workflow_runs")
    op.drop_index("ix_novel_workflow_runs_status_last_heartbeat_at", table_name="novel_workflow_runs")
    op.drop_index("ix_novel_workflow_runs_status_attempt_count_created_at", table_name="novel_workflow_runs")
    op.drop_index("ix_novel_workflow_runs_status_created_at", table_name="novel_workflow_runs")
    op.drop_table("novel_workflow_runs")
    op.drop_column("project_chapters", "beats_markdown")
    op.drop_column("project_bibles", "story_summary")
