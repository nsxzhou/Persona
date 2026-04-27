"""split characters into blueprint and status

Revision ID: f6a7b8c9d0e1
Revises: f5a6b7c8d9e0
Create Date: 2026-04-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    with op.batch_alter_table('project_bibles') as batch_op:
        batch_op.add_column(sa.Column('characters_blueprint', sa.Text(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('characters_status', sa.Text(), nullable=False, server_default=''))
    
    with op.batch_alter_table('project_chapters') as batch_op:
        batch_op.add_column(sa.Column('memory_sync_proposed_characters_status', sa.Text(), nullable=True))
    
    # Migrate data
    op.execute("UPDATE project_bibles SET characters_blueprint = characters")
    
    # Drop old column
    with op.batch_alter_table('project_bibles') as batch_op:
        batch_op.drop_column('characters')


def downgrade() -> None:
    # Add back old column
    with op.batch_alter_table('project_bibles') as batch_op:
        batch_op.add_column(sa.Column('characters', sa.Text(), nullable=False, server_default=''))
    
    # Migrate data back
    op.execute("UPDATE project_bibles SET characters = characters_blueprint")
    
    # Drop new columns
    with op.batch_alter_table('project_bibles') as batch_op:
        batch_op.drop_column('characters_blueprint')
        batch_op.drop_column('characters_status')

    with op.batch_alter_table('project_chapters') as batch_op:
        batch_op.drop_column('memory_sync_proposed_characters_status')
