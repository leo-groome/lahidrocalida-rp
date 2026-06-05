"""v3: rename password to pin, add turno_id to pedidos, create registros_asistencia

Revision ID: a1b2c3d4e5f6
Revises: 403c2d470135
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '403c2d470135'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Usar argon2 (scheme principal del proyecto, sin límite de 72 bytes)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
DEFAULT_PIN_HASH = pwd_context.hash("1111")


def upgrade() -> None:
    # 1. Renombrar columna password → pin en usuarios
    op.alter_column(
        'usuarios',
        'password',
        new_column_name='pin',
        existing_type=sa.String(255),
        existing_nullable=False,
    )

    # 2. Resetear todos los PINs a hash de "1111"
    op.execute(
        sa.text("UPDATE usuarios SET pin = :pin_hash").bindparams(pin_hash=DEFAULT_PIN_HASH)
    )

    # 3. Añadir turno_id a pedidos
    op.add_column(
        'pedidos',
        sa.Column('turno_id', sa.Integer(), sa.ForeignKey('turnos.id'), nullable=True)
    )
    op.create_index('ix_pedidos_turno_id', 'pedidos', ['turno_id'])

    # 4. Crear tabla registros_asistencia
    op.create_table(
        'registros_asistencia',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=False),
        sa.Column('fecha_entrada', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fecha_salida', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notas', sa.Text(), nullable=True),
    )
    op.create_index('ix_registros_asistencia_usuario_id', 'registros_asistencia', ['usuario_id'])


def downgrade() -> None:
    # 4. Eliminar tabla registros_asistencia
    op.drop_index('ix_registros_asistencia_usuario_id', table_name='registros_asistencia')
    op.drop_table('registros_asistencia')

    # 3. Eliminar turno_id de pedidos
    op.drop_index('ix_pedidos_turno_id', table_name='pedidos')
    op.drop_column('pedidos', 'turno_id')

    # 1. Renombrar pin → password (downgrade no restaura valores originales)
    op.alter_column(
        'usuarios',
        'pin',
        new_column_name='password',
        existing_type=sa.String(255),
        existing_nullable=False,
    )
