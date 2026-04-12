"""migrate style lab payloads to markdown text

Revision ID: 0010_markdown_style_lab_payloads
Revises: 0009_user_scoped_resources
Create Date: 2026-04-12 14:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0010_markdown_style_lab_payloads"
down_revision = "0009_user_scoped_resources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE projects SET style_profile_id = NULL WHERE style_profile_id IS NOT NULL"))
    op.execute(sa.text("DELETE FROM style_profiles"))
    op.execute(
        sa.text(
            """
            UPDATE style_analysis_jobs
            SET analysis_report_payload = NULL,
                style_summary_payload = NULL,
                prompt_pack_payload = NULL
            WHERE analysis_report_payload IS NOT NULL
               OR style_summary_payload IS NOT NULL
               OR prompt_pack_payload IS NOT NULL
            """
        )
    )

    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.alter_column(
            "analysis_report_payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "style_summary_payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "prompt_pack_payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            nullable=True,
        )

    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.alter_column(
            "analysis_report_payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            nullable=False,
        )
        batch_op.alter_column(
            "style_summary_payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            nullable=False,
        )
        batch_op.alter_column(
            "prompt_pack_payload",
            existing_type=sa.JSON(),
            type_=sa.Text(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("style_profiles") as batch_op:
        batch_op.alter_column(
            "analysis_report_payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            nullable=False,
        )
        batch_op.alter_column(
            "style_summary_payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            nullable=False,
        )
        batch_op.alter_column(
            "prompt_pack_payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            nullable=False,
        )

    with op.batch_alter_table("style_analysis_jobs") as batch_op:
        batch_op.alter_column(
            "analysis_report_payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            nullable=True,
        )
        batch_op.alter_column(
            "style_summary_payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            nullable=True,
        )
        batch_op.alter_column(
            "prompt_pack_payload",
            existing_type=sa.Text(),
            type_=sa.JSON(),
            nullable=True,
        )
