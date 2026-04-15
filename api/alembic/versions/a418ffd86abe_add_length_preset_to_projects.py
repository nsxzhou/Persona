"""add length_preset to projects

Revision ID: a418ffd86abe
Revises: a1b2c3d4e5f6
Create Date: 2026-04-15 18:10:32.162804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a418ffd86abe'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('length_preset', sa.String(length=16), nullable=False, server_default='short'))


def downgrade() -> None:
    op.drop_column('projects', 'length_preset')
