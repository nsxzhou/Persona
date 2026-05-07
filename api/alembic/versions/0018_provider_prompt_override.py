"""add provider immersion prompt override

Revision ID: 0018_provider_prompt_override
Revises: 0017_profile_payload_names
Create Date: 2026-05-07 14:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0018_provider_prompt_override"
down_revision = "0017_profile_payload_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("provider_configs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "immersion_prompt_override_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "immersion_system_prompt_suffix",
                sa.Text(),
                nullable=False,
                server_default="",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("provider_configs", schema=None) as batch_op:
        batch_op.drop_column("immersion_system_prompt_suffix")
        batch_op.drop_column("immersion_prompt_override_enabled")
