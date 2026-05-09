"""add provider chat test system prompt

Revision ID: 0020_provider_chat_test_prompt
Revises: 0019_project_prompt_assets
Create Date: 2026-05-09 14:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_provider_chat_test_prompt"
down_revision = "0019_project_prompt_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("provider_configs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "chat_test_system_prompt",
                sa.Text(),
                nullable=False,
                server_default="",
            )
        )
    op.execute(
        "UPDATE provider_configs "
        "SET chat_test_system_prompt = immersion_system_prompt_suffix "
        "WHERE chat_test_system_prompt = '' "
        "AND immersion_system_prompt_suffix IS NOT NULL "
        "AND immersion_system_prompt_suffix != ''"
    )


def downgrade() -> None:
    with op.batch_alter_table("provider_configs", schema=None) as batch_op:
        batch_op.drop_column("chat_test_system_prompt")
