"""split story_bible into runtime_state and runtime_threads

Revision ID: b1c2d3e4f5a6
Revises: a418ffd86abe
Create Date: 2026-04-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a418ffd86abe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'projects',
        sa.Column('runtime_state', sa.Text(), nullable=False, server_default=''),
    )
    op.add_column(
        'projects',
        sa.Column('runtime_threads', sa.Text(), nullable=False, server_default=''),
    )
    # Migrate existing story_bible content to runtime_state
    op.execute("UPDATE projects SET runtime_state = story_bible")
    op.drop_column('projects', 'story_bible')


def downgrade() -> None:
    op.add_column(
        'projects',
        sa.Column('story_bible', sa.Text(), nullable=False, server_default=''),
    )
    # Migrate runtime_state content back to story_bible
    op.execute("UPDATE projects SET story_bible = runtime_state")
    op.drop_column('projects', 'runtime_state')
    op.drop_column('projects', 'runtime_threads')
