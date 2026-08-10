"""nomina: proveedor_id nullable + tabla nomina_detalles

Revision ID: c4d5e6f7a8b9
Revises: e8f7d6c5b4a3
Create Date: 2026-08-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'e8f7d6c5b4a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. La nómina no lleva proveedor: relajar NOT NULL.
    op.alter_column('gastos', 'proveedor_id',
                    existing_type=sa.Integer(),
                    nullable=True)

    # 2. Líneas de pago a empleados dentro de una tanda de nómina.
    op.create_table(
        'nomina_detalles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gasto_id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('monto', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('notas', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gasto_id'], ['gastos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_nomina_detalles_id', 'nomina_detalles', ['id'], unique=False)
    op.create_index('ix_nomina_detalles_gasto_id', 'nomina_detalles', ['gasto_id'], unique=False)
    op.create_index('ix_nomina_detalles_usuario_id', 'nomina_detalles', ['usuario_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_nomina_detalles_usuario_id', table_name='nomina_detalles')
    op.drop_index('ix_nomina_detalles_gasto_id', table_name='nomina_detalles')
    op.drop_index('ix_nomina_detalles_id', table_name='nomina_detalles')
    op.drop_table('nomina_detalles')

    op.alter_column('gastos', 'proveedor_id',
                    existing_type=sa.Integer(),
                    nullable=False)
