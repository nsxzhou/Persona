"""add_story_bible_fields

Revision ID: a1b2c3d4e5f6
Revises: 0ed5f4b2b7d7
Create Date: 2026-04-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0ed5f4b2b7d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STORY_BIBLE_COLUMNS = [
    'inspiration',
    'world_building',
    'characters',
    'outline_master',
    'outline_detail',
    'story_bible',
]


def upgrade() -> None:
    for col in _STORY_BIBLE_COLUMNS:
        op.add_column(
            'projects',
            sa.Column(col, sa.Text(), nullable=False, server_default=''),
        )


def downgrade() -> None:
    for col in reversed(_STORY_BIBLE_COLUMNS):
        op.drop_column('projects', col)
