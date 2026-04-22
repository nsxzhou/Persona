"""analysis stage renames

Revision ID: 0014_analysis_stage_renames
Revises: ea8aaba06296
Create Date: 2026-04-22 21:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_analysis_stage_renames"
down_revision = "ea8aaba06296"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE style_analysis_jobs
            SET stage = 'postprocessing'
            WHERE stage IN ('summarizing', 'composing_prompt_pack')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE plot_analysis_jobs
            SET stage = 'analyzing_focus_chunks'
            WHERE stage = 'analyzing_chunks'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE plot_analysis_jobs
            SET stage = 'postprocessing'
            WHERE stage IN ('summarizing', 'composing_prompt_pack')
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE style_analysis_jobs
            SET stage = 'summarizing'
            WHERE stage = 'postprocessing'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE plot_analysis_jobs
            SET stage = 'analyzing_chunks'
            WHERE stage = 'analyzing_focus_chunks'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE plot_analysis_jobs
            SET stage = 'summarizing'
            WHERE stage = 'postprocessing'
            """
        )
    )
