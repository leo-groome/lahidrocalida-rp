"""Add estado_item column to articulos_pedido table

Revision ID: 002_add_estado_item
Revises: 001_add_kds_name
Create Date: 2025-10-28 13:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_estado_item'
down_revision = '001_add_kds_name'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('articulos_pedido', sa.Column('estado_item', sa.String(20), server_default='pendiente', nullable=False))


def downgrade() -> None:
    op.drop_column('articulos_pedido', 'estado_item')
