"""add client_request_id to pedidos for idempotent creation

Revision ID: b7c9e2d41a08
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c9e2d41a08'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pedidos', sa.Column('client_request_id', sa.String(length=36), nullable=True))
    op.create_index(
        'uq_pedidos_client_request_id',
        'pedidos',
        ['client_request_id'],
        unique=True,
        postgresql_where=sa.text('client_request_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_pedidos_client_request_id', table_name='pedidos')
    op.drop_column('pedidos', 'client_request_id')
