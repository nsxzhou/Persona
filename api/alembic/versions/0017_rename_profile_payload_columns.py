"""rename profile payload columns

Revision ID: 0017_profile_payload_names
Revises: 0016_novel_workflows
Create Date: 2026-04-27 16:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_profile_payload_names"
down_revision = "0016_novel_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_analysis_jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("voice_profile_payload", sa.Text(), nullable=True))
    op.execute(
        "UPDATE style_analysis_jobs SET voice_profile_payload = prompt_pack_payload"
    )
    with op.batch_alter_table("style_analysis_jobs", schema=None) as batch_op:
        batch_op.drop_column("style_summary_payload")
        batch_op.drop_column("prompt_pack_payload")

    with op.batch_alter_table("style_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("voice_profile_payload", sa.Text(), nullable=False, server_default="")
        )
    op.execute("UPDATE style_profiles SET voice_profile_payload = prompt_pack_payload")
    with op.batch_alter_table("style_profiles", schema=None) as batch_op:
        batch_op.drop_column("style_summary_payload")
        batch_op.drop_column("prompt_pack_payload")
        batch_op.alter_column("voice_profile_payload", server_default=None)

    with op.batch_alter_table("plot_analysis_jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("story_engine_payload", sa.Text(), nullable=True))
    op.execute(
        "UPDATE plot_analysis_jobs SET story_engine_payload = prompt_pack_payload"
    )
    with op.batch_alter_table("plot_analysis_jobs", schema=None) as batch_op:
        batch_op.drop_column("plot_summary_payload")
        batch_op.drop_column("prompt_pack_payload")

    with op.batch_alter_table("plot_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("story_engine_payload", sa.Text(), nullable=False, server_default="")
        )
    op.execute("UPDATE plot_profiles SET story_engine_payload = prompt_pack_payload")
    with op.batch_alter_table("plot_profiles", schema=None) as batch_op:
        batch_op.drop_column("plot_summary_payload")
        batch_op.drop_column("prompt_pack_payload")
        batch_op.alter_column("story_engine_payload", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("plot_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("prompt_pack_payload", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("plot_summary_payload", sa.Text(), nullable=False, server_default="")
        )
    op.execute("UPDATE plot_profiles SET prompt_pack_payload = story_engine_payload")
    with op.batch_alter_table("plot_profiles", schema=None) as batch_op:
        batch_op.drop_column("story_engine_payload")
        batch_op.alter_column("prompt_pack_payload", server_default=None)
        batch_op.alter_column("plot_summary_payload", server_default=None)

    with op.batch_alter_table("plot_analysis_jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("prompt_pack_payload", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("plot_summary_payload", sa.Text(), nullable=True))
    op.execute("UPDATE plot_analysis_jobs SET prompt_pack_payload = story_engine_payload")
    with op.batch_alter_table("plot_analysis_jobs", schema=None) as batch_op:
        batch_op.drop_column("story_engine_payload")

    with op.batch_alter_table("style_profiles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("prompt_pack_payload", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("style_summary_payload", sa.Text(), nullable=False, server_default="")
        )
    op.execute("UPDATE style_profiles SET prompt_pack_payload = voice_profile_payload")
    with op.batch_alter_table("style_profiles", schema=None) as batch_op:
        batch_op.drop_column("voice_profile_payload")
        batch_op.alter_column("prompt_pack_payload", server_default=None)
        batch_op.alter_column("style_summary_payload", server_default=None)

    with op.batch_alter_table("style_analysis_jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("prompt_pack_payload", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("style_summary_payload", sa.Text(), nullable=True))
    op.execute("UPDATE style_analysis_jobs SET prompt_pack_payload = voice_profile_payload")
    with op.batch_alter_table("style_analysis_jobs", schema=None) as batch_op:
        batch_op.drop_column("voice_profile_payload")
