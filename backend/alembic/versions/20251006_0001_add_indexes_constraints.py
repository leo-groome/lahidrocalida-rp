"""add indexes and constraints non destructive

Revision ID: 20251006_0001
Revises: 
Create Date: 2025-10-06 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251006_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Índices sugeridos
    op.create_index('ix_pedidos_estado', 'pedidos', ['estado'], unique=False)
    op.create_index('ix_pedidos_fecha_creacion', 'pedidos', ['fecha_creacion'], unique=False)
    op.create_index('ix_articulos_pedido_pedido_id', 'articulos_pedido', ['pedido_id'], unique=False)
    op.create_index('ix_platillos_categoria', 'platillos', ['categoria'], unique=False)

    # Unique en numero_display si no existe ya
    # Usamos try/except por si ya existe en el entorno
    try:
        op.create_unique_constraint('uq_pedidos_numero_display', 'pedidos', ['numero_display'])
    except Exception:
        pass


def downgrade() -> None:
    # Revertir índices
    op.drop_index('ix_platillos_categoria', table_name='platillos')
    op.drop_index('ix_articulos_pedido_pedido_id', table_name='articulos_pedido')
    op.drop_index('ix_pedidos_fecha_creacion', table_name='pedidos')
    op.drop_index('ix_pedidos_estado', table_name='pedidos')

    # Revertir unique
    try:
        op.drop_constraint('uq_pedidos_numero_display', 'pedidos', type_='unique')
    except Exception:
        pass


