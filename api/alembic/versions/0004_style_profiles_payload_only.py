"""style profiles payload only

Revision ID: 0004_style_profiles_payload_only
Revises: 0003_deep_analysis_results
Create Date: 2026-04-09 22:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_style_profiles_payload_only"
down_revision = "0003_deep_analysis_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM style_profiles
            WHERE analysis_report_payload IS NULL
               OR style_summary_payload IS NULL
               OR prompt_pack_payload IS NULL
            """
        )
    )
    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.drop_column("analysis_summary")
        batch_op.drop_column("global_system_prompt")
        batch_op.drop_column("dimensions")
        batch_op.drop_column("scene_prompts")
        batch_op.drop_column("few_shot_examples")
        batch_op.alter_column("analysis_report_payload", existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column("style_summary_payload", existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column("prompt_pack_payload", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.add_column(sa.Column("analysis_summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("global_system_prompt", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("dimensions", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("scene_prompts", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("few_shot_examples", sa.JSON(), nullable=True))
        batch_op.alter_column("analysis_report_payload", existing_type=sa.JSON(), nullable=True)
        batch_op.alter_column("style_summary_payload", existing_type=sa.JSON(), nullable=True)
        batch_op.alter_column("prompt_pack_payload", existing_type=sa.JSON(), nullable=True)
