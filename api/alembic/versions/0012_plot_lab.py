"""plot lab

Revision ID: 0012_plot_lab
Revises: f5a6b7c8d9e0
Create Date: 2026-04-21 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_plot_lab"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plot_sample_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plot_sample_files_user_id"), "plot_sample_files", ["user_id"], unique=False)

    op.create_table(
        "plot_analysis_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("plot_name", sa.String(length=120), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("sample_file_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("analysis_meta_payload", sa.JSON(), nullable=True),
        sa.Column("analysis_report_payload", sa.Text(), nullable=True),
        sa.Column("plot_summary_payload", sa.Text(), nullable=True),
        sa.Column("prompt_pack_payload", sa.Text(), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_configs.id"]),
        sa.ForeignKeyConstraint(["sample_file_id"], ["plot_sample_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_file_id"),
    )
    op.create_index("ix_plot_analysis_jobs_status_created_at", "plot_analysis_jobs", ["status", "created_at"], unique=False)
    op.create_index("ix_plot_analysis_jobs_status_attempt_count_created_at", "plot_analysis_jobs", ["status", "attempt_count", "created_at"], unique=False)
    op.create_index("ix_plot_analysis_jobs_status_last_heartbeat_at", "plot_analysis_jobs", ["status", "last_heartbeat_at"], unique=False)
    op.create_index(op.f("ix_plot_analysis_jobs_status"), "plot_analysis_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_plot_analysis_jobs_user_id"), "plot_analysis_jobs", ["user_id"], unique=False)

    op.create_table(
        "plot_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source_job_id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("plot_name", sa.String(length=120), nullable=False),
        sa.Column("analysis_report_payload", sa.Text(), nullable=False),
        sa.Column("plot_summary_payload", sa.Text(), nullable=False),
        sa.Column("prompt_pack_payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_configs.id"]),
        sa.ForeignKeyConstraint(["source_job_id"], ["plot_analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_job_id"),
    )
    op.create_index(op.f("ix_plot_profiles_provider_id"), "plot_profiles", ["provider_id"], unique=False)
    op.create_index(op.f("ix_plot_profiles_user_id"), "plot_profiles", ["user_id"], unique=False)

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plot_profile_id", sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f("ix_projects_plot_profile_id"), ["plot_profile_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_projects_plot_profile_id",
            "plot_profiles",
            ["plot_profile_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_constraint("fk_projects_plot_profile_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_projects_plot_profile_id"))
        batch_op.drop_column("plot_profile_id")

    op.drop_index(op.f("ix_plot_profiles_user_id"), table_name="plot_profiles")
    op.drop_index(op.f("ix_plot_profiles_provider_id"), table_name="plot_profiles")
    op.drop_table("plot_profiles")

    op.drop_index(op.f("ix_plot_analysis_jobs_user_id"), table_name="plot_analysis_jobs")
    op.drop_index(op.f("ix_plot_analysis_jobs_status"), table_name="plot_analysis_jobs")
    op.drop_index("ix_plot_analysis_jobs_status_last_heartbeat_at", table_name="plot_analysis_jobs")
    op.drop_index("ix_plot_analysis_jobs_status_attempt_count_created_at", table_name="plot_analysis_jobs")
    op.drop_index("ix_plot_analysis_jobs_status_created_at", table_name="plot_analysis_jobs")
    op.drop_table("plot_analysis_jobs")

    op.drop_index(op.f("ix_plot_sample_files_user_id"), table_name="plot_sample_files")
    op.drop_table("plot_sample_files")
