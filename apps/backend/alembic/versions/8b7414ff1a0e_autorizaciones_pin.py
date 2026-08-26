"""autorizaciones_pin: auditoría de acciones autorizadas con PIN de admin

Revision ID: 8b7414ff1a0e
Revises: baca83828037
Create Date: 2026-08-26 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b7414ff1a0e"
down_revision: Union[str, None] = "baca83828037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No hay cajero fijo: la sesión de caja la comparte cualquier mesero de
    # confianza, así que borrar artículo, cancelar cuenta, editar propina de
    # un ticket pagado y ver analíticas del turno ahora exigen PIN de un
    # administrador activo. Esta tabla registra quién ejecutó la acción y
    # qué administrador la autorizó (no se elige de una lista — se guarda
    # cuál hash de PIN hizo match).
    op.create_table(
        "autorizaciones_pin",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("accion", sa.String(length=50), nullable=False),
        sa.Column("ejecutado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("autorizado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("pedido_id", sa.Integer(), sa.ForeignKey("pedidos.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_autorizaciones_pin_accion_created_at",
        "autorizaciones_pin",
        ["accion", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_autorizaciones_pin_accion_created_at", table_name="autorizaciones_pin")
    op.drop_table("autorizaciones_pin")
