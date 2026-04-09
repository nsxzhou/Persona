"""style lab schema

Revision ID: 0002_style_lab
Revises: 0001_initial
Create Date: 2026-04-09 13:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_style_lab"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "style_sample_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "style_analysis_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("style_name", sa.String(length=120), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("sample_file_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("draft_payload", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_configs.id"]),
        sa.ForeignKeyConstraint(["sample_file_id"], ["style_sample_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_file_id"),
    )

    op.create_table(
        "style_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_job_id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("style_name", sa.String(length=120), nullable=False),
        sa.Column("analysis_summary", sa.Text(), nullable=False),
        sa.Column("global_system_prompt", sa.Text(), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("scene_prompts", sa.JSON(), nullable=False),
        sa.Column("few_shot_examples", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_configs.id"]),
        sa.ForeignKeyConstraint(["source_job_id"], ["style_analysis_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_job_id"),
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.create_foreign_key(
            "fk_projects_style_profile_id",
            "style_profiles",
            ["style_profile_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_style_profile_id", type_="foreignkey")

    op.drop_table("style_profiles")
    op.drop_table("style_analysis_jobs")
    op.drop_table("style_sample_files")

