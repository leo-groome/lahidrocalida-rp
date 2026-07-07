"""add idempotency columns

Revision ID: e8f7d6c5b4a3
Revises: b7c9e2d41a08
Create Date: 2026-07-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f7d6c5b4a3'
down_revision: Union[str, None] = 'b7c9e2d41a08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. parent_pedido_id in pedidos
    op.add_column('pedidos', sa.Column('parent_pedido_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_pedidos_parent_pedido_id', 'pedidos', 'pedidos', ['parent_pedido_id'], ['id'])
    op.create_index('ix_pedidos_parent_pedido_id', 'pedidos', ['parent_pedido_id'], unique=False)

    # 2. client_request_id in articulos_pedido
    op.add_column('articulos_pedido', sa.Column('client_request_id', sa.String(length=36), nullable=True))
    op.create_index('ix_articulos_pedido_client_request_id', 'articulos_pedido', ['client_request_id'], unique=False)


def downgrade() -> None:
    # 1. Remove from articulos_pedido
    op.drop_index('ix_articulos_pedido_client_request_id', table_name='articulos_pedido')
    op.drop_column('articulos_pedido', 'client_request_id')

    # 2. Remove from pedidos
    op.drop_index('ix_pedidos_parent_pedido_id', table_name='pedidos')
    op.drop_constraint('fk_pedidos_parent_pedido_id', 'pedidos', type_='foreignkey')
    op.drop_column('pedidos', 'parent_pedido_id')
