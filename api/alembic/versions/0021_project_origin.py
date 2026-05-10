"""add project origin

Revision ID: 0021_project_origin
Revises: 0020_provider_chat_test_prompt
Create Date: 2026-05-10 17:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_project_origin"
down_revision = "0020_provider_chat_test_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "project_origin",
                sa.String(length=32),
                nullable=False,
                server_default="normal",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("project_origin")
