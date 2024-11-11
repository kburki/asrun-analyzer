"""Add unique constraints

Revision ID: b4fe8916f621
Revises: ea63dc4f4880
Create Date: 2024-11-10 21:55:40.633870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4fe8916f621'
down_revision: Union[str, None] = 'ea63dc4f4880'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('uix_event_id_start_time', 'events', ['event_id', 'start_time'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('uix_event_id_start_time', 'events', type_='unique')
    # ### end Alembic commands ###