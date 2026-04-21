"""backfill project.description from inspiration

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-04-20 12:00:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE projects
        SET description = inspiration
        WHERE (description IS NULL OR description = '')
          AND inspiration IS NOT NULL
          AND inspiration <> ''
        """
    )


def downgrade() -> None:
    # 回填动作不可逆；inspiration 列仍存在，数据未丢失，故 downgrade 空操作
    pass
