"""add tipo_orden to pedidos

Revision ID: 20251006_0002
Revises: 20251006_0001
Create Date: 2025-10-06 00:10:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251006_0002'
down_revision = '20251006_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pedidos', sa.Column('tipo_orden', sa.String(length=20), nullable=True))
    # Set default 'aqui' for existing rows
    op.execute("UPDATE pedidos SET tipo_orden = 'aqui' WHERE tipo_orden IS NULL")
    # Make non-nullable going forward with server default
    op.alter_column('pedidos', 'tipo_orden', existing_type=sa.String(length=20), nullable=False, server_default='aqui')
    # Optional index if filtering by tipo_orden becomes common
    op.create_index('ix_pedidos_tipo_orden', 'pedidos', ['tipo_orden'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_pedidos_tipo_orden', table_name='pedidos')
    op.drop_column('pedidos', 'tipo_orden')


